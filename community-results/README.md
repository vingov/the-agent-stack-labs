# Community results

This directory will contain maintainer-reviewed, sanitized compatibility results.

Start with a **Lab result** issue instead of opening a pull request directly. After the evidence boundary is reviewed, a result may be added using this layout:

~~~text
community-results/
  <lab-id>/
    <project-version>/
      <os-provider-or-runtime>/
        result.json
        README.md
~~~

Results should contain counts, hashes, booleans, and evidence classes. Never publish raw provider payloads, prompts, profile files, or session databases.
