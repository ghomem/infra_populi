# Runs ON puppet8master over `puppet catalog compile` output (step 2.2). Prints ONLY counts, class
# names and Type[title] of target-tagged resources -- never parameters, never the raw catalog, not even
# on a parse error (ruling 6a: the catalog carries the lab-local passwd_common).
# ARGV: target class names. Exit 0 ok, 3 a target has no concrete resources, 4 no parseable catalog.
# A `digest_paths` file beside this script (compile-only --file-digest, HQ 2026-11-18 ruling A1) lists File titles, one
# per line: each gets a sha256 and a byte count of its rendered content, never the content itself, and never for a
# passwd_common resource.
require 'json'
require 'digest'
raw = STDIN.read
start = raw.index('{"tags"')
catalog = nil
begin
  catalog = JSON.parse(raw[start..]) if start
rescue StandardError
  catalog = nil
end
unless catalog.is_a?(Hash) && catalog['resources'].is_a?(Array)
  puts 'COMPILE_FILTER: compiler output did not contain a parseable catalog (output withheld)'
  exit 4
end
skip = %w[Class Stage Node]
res = catalog['resources']
pi = Array(catalog['classes']).select { |c| c.start_with?('puppet_infrastructure::') }
puts "CATALOG: #{res.size} resources; puppet_infrastructure classes: #{pi.join(' ')}"
empty = 0
ARGV.each do |target|
  tag = target.downcase
  mine = res.select { |r| Array(r['tags']).include?(tag) && !skip.include?(r['type']) }
  concrete = mine.reject { |r| r['type'].include?('::') }
  puts "COMPILE_COVERAGE #{target}: #{concrete.size} concrete resources (+#{mine.size - concrete.size} defined-type instances)"
  mine.each { |r| puts "  #{r['type']}[#{r['title']}]" }
  empty += 1 if concrete.empty?
end
digest_list = File.join(File.dirname(__FILE__), 'digest_paths')
if File.exist?(digest_list)
  File.readlines(digest_list, chomp: true).reject(&:empty?).each do |path|
    file = res.find { |r| r['type'] == 'File' && r['title'] == path }
    if file.nil?
      puts "FILE_DIGEST #{path}: not in the catalog"
    elsif Array(file['tags']).include?('passwd_common')
      puts "FILE_DIGEST #{path}: withheld (passwd_common, ruling 6a)"
    elsif !file.fetch('parameters', {}).key?('content')
      puts "FILE_DIGEST #{path}: no content parameter"
    else
      content = file['parameters']['content'].to_s
      puts "FILE_DIGEST #{path}: sha256:#{Digest::SHA256.hexdigest(content)} bytes:#{content.bytesize}"
    end
  end
end
pc = res.select { |r| Array(r['tags']).include?('passwd_common') && !skip.include?(r['type']) }
puts "PASSWD_COMMON: #{pc.size} resources (lab-local, ruling 6a)#{pc.empty? ? '' : ': '}#{pc.map { |r| "#{r['type']}[#{r['title']}]" }.join(' ')}"
exit(empty.positive? ? 3 : 0)
