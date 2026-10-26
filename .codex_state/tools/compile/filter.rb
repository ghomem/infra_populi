# Runs ON puppet8master over `puppet catalog compile` output (step 2.2). Prints ONLY counts, class
# names and Type[title] of target-tagged resources -- never parameters, never the raw catalog, not even
# on a parse error (ruling 6a: the catalog carries the lab-local passwd_common).
# ARGV: target class names. Exit 0 ok, 3 a target has no concrete resources, 4 no parseable catalog.
require 'json'
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
pc = res.select { |r| Array(r['tags']).include?('passwd_common') && !skip.include?(r['type']) }
puts "PASSWD_COMMON: #{pc.size} resources (lab-local, ruling 6a)#{pc.empty? ? '' : ': '}#{pc.map { |r| "#{r['type']}[#{r['title']}]" }.join(' ')}"
exit(empty.positive? ? 3 : 0)
