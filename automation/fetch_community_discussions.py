#!/usr/bin/env python3
"""Fetch the public OPSOAI community feed from GitHub Discussions."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "_data" / "community.json"
OUTPUT_PATH = ROOT / "_data" / "community_discussions.json"
GRAPHQL_URL = "https://api.github.com/graphql"

CATEGORY_QUERY = """
query CommunityCategories($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    discussionCategories(first: 25) {
      nodes {
        id
        name
        slug
      }
    }
  }
}
"""

DISCUSSION_FIELDS = """
nodes {
  number
  title
  url
  createdAt
  updatedAt
  isAnswered
  upvoteCount
  comments {
    totalCount
  }
  author {
    login
  }
  category {
    name
    slug
  }
}
"""


def graphql_request(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Run one authenticated GitHub GraphQL request."""
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "opsoai-community-feed",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub GraphQL HTTP {error.code}: {detail}") from error

    if payload.get("errors"):
        raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")

    return payload["data"]


def build_discussions_query(category_count: int) -> str:
    """Build a query that fetches each community category independently."""
    variable_definitions = [
        "$owner: String!",
        "$name: String!",
        *[f"$category{index}: ID!" for index in range(category_count)],
    ]
    category_fields = [
        (
            f"category{index}: discussions("
            f"first: 12, categoryId: $category{index}, "
            "orderBy: {field: UPDATED_AT, direction: DESC}"
            f") {{ {DISCUSSION_FIELDS} }}"
        )
        for index in range(category_count)
    ]
    definitions = ", ".join(variable_definitions)
    fields = "\n".join(category_fields)
    return (
        f"query CommunityDiscussions({definitions}) {{\n"
        f"  repository(owner: $owner, name: $name) {{\n{fields}\n  }}\n"
        "}"
    )


def normalize_discussions(
    connections: list[dict[str, Any]], allowed_slugs: set[str], limit: int
) -> list[dict[str, Any]]:
    """Flatten, validate, sort and minimize the data rendered on the site."""
    by_number: dict[int, dict[str, Any]] = {}

    for connection in connections:
        for node in connection.get("nodes") or []:
            category = node.get("category") or {}
            slug = category.get("slug")
            if slug not in allowed_slugs:
                continue

            author = node.get("author") or {}
            title = " ".join(str(node.get("title") or "").split())
            by_number[int(node["number"])] = {
                "number": int(node["number"]),
                "title": title[:240],
                "url": str(node["url"]),
                "category": {
                    "name": str(category.get("name") or ""),
                    "slug": str(slug),
                },
                "author": str(author.get("login") or "ghost"),
                "created_at": str(node["createdAt"]),
                "updated_at": str(node["updatedAt"]),
                "comments": int((node.get("comments") or {}).get("totalCount") or 0),
                "upvotes": int(node.get("upvoteCount") or 0),
                "answered": bool(node.get("isAnswered")),
            }

    ordered = sorted(
        by_number.values(),
        key=lambda discussion: discussion["updated_at"],
        reverse=True,
    )
    return ordered[:limit]


def write_feed(discussions: list[dict[str, Any]]) -> None:
    """Atomically replace the Jekyll data file."""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "discussions": discussions,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=OUTPUT_PATH.parent,
        prefix=".community-discussions-",
        suffix=".json",
        delete=False,
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary_path = Path(handle.name)
    temporary_path.replace(OUTPUT_PATH)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print("GITHUB_TOKEN is required to refresh the community feed.", file=sys.stderr)
        return 2

    with CONFIG_PATH.open(encoding="utf-8") as handle:
        config = json.load(handle)

    owner, name = config["repository"].split("/", 1)
    requested_slugs = [category["slug"] for category in config["categories"]]
    variables = {"owner": owner, "name": name}

    category_data = graphql_request(token, CATEGORY_QUERY, variables)
    repository = category_data.get("repository")
    if repository is None:
        raise RuntimeError(f"Repository not found: {config['repository']}")

    categories = {
        category["slug"]: category
        for category in repository["discussionCategories"]["nodes"]
    }
    missing = [slug for slug in requested_slugs if slug not in categories]
    if missing:
        raise RuntimeError(f"Missing Discussion categories: {', '.join(missing)}")

    category_variables = {
        f"category{index}": categories[slug]["id"]
        for index, slug in enumerate(requested_slugs)
    }
    discussion_data = graphql_request(
        token,
        build_discussions_query(len(requested_slugs)),
        {**variables, **category_variables},
    )
    connections = [
        discussion_data["repository"][f"category{index}"]
        for index in range(len(requested_slugs))
    ]
    discussions = normalize_discussions(
        connections,
        set(requested_slugs),
        int(config.get("feed_limit", 12)),
    )
    write_feed(discussions)
    print(f"Refreshed community feed with {len(discussions)} discussions.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # Keep the workflow log concise and actionable.
        print(f"Unable to refresh community feed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
