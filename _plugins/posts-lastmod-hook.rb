#!/usr/bin/env ruby

# Read the repository history once. The previous hook spawned one or two Git
# processes per post, which made a 600+ post production build unnecessarily
# slow. The newest occurrence of a path is its last modification.
Jekyll::Hooks.register :site, :after_init do |site|
  newest = {}
  counts = Hash.new(0)
  current_date = nil

  output = Dir.chdir(site.source) do
    IO.popen(
      ['git', '-c', 'core.quotePath=false', 'log', '--format=@@@%aI', '--name-only', '--', '_posts'],
      &:read
    )
  end

  output.each_line do |line|
    value = line.strip
    if value.start_with?('@@@')
      current_date = value.delete_prefix('@@@')
    elsif value.start_with?('_posts/')
      counts[value] += 1
      newest[value] ||= current_date
    end
  end

  site.config['post_lastmod_dates'] = newest
  site.config['post_commit_counts'] = counts
rescue StandardError => error
  Jekyll.logger.warn 'lastmod:', "Git history unavailable (#{error.message})"
  site.config['post_lastmod_dates'] = {}
  site.config['post_commit_counts'] = {}
end

Jekyll::Hooks.register :posts, :post_init do |post|
  # `summary` is the editorial deck used throughout this repository. Expose it
  # through Jekyll's standard field so SEO tags, cards and feeds all reuse it.
  post.data['description'] ||= post.data['summary']

  path = post.relative_path.to_s.delete_prefix('/')
  counts = post.site.config['post_commit_counts'] || {}
  dates = post.site.config['post_lastmod_dates'] || {}
  post.data['last_modified_at'] = dates[path] if counts[path].to_i > 1 && dates[path]
end
