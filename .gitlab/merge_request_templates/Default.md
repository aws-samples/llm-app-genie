# \[Replace with Title\]

### Description

Describe the problem or task that this merge request addressed.

### Related Issues

If applicable reference the issues this merge request fixes.

- fixes #issue-number

### Additional Notes

Include any extra information or considerations for reviewers, such as impacted areas of the codebase.

### Merge Request Checklists

- [ ] I am using [conventional commit types](https://www.conventionalcommits.org/en/v1.0.0/) for my merge request title. Your title should follow the structure `<type>([optional scope]):<description>`.

  Common types are:

  - feat (for enhancements)
  - bug (for bug fixes)
  - docs (for changes to the documentation)
  - test (for changes to the tests)
  - perf (for performance improvements)
  - refactor (for code refactorings)

  If your change is breaking backwards compatibility use a ! after the type to indicate that your merge request contains breaking changes.

  Examples:

  - feat(chatbot): add local document upload
  - bug: fix CodePipeline
  - refactor!: change environment variable names

- [ ] I fixed any [trunk](../../README.md#pre-requisites-for-development) issues.
      Code follows project coding guidelines.
- [ ] I updated the documentation to reflect the changes
- [ ] I tagged this merge request with the next MINOR [semver](https://semver.org/) version number or with the next PATH version number if it is a bug fix. You can find the prior version in GitLab in Issues > Milestones. If the highest version number in the Milestones is `v1.0.1` and this merge request is for a bug fix then you should create a new milestone `v1.0.2` (PATCH version increased by one) and tag this merge request with milestone `v1.0.1`. If your merge request is a change other than fixing a bug then you should create a new milestone with `v1.1.0` (MINOR version increased by one) and use it to tag this merge request.

**By submitting this pull request, I confirm that my contribution is made under the terms of the [MIT-0](../../LICENSE).**
