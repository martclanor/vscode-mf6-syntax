# Changelog

## 0.2.1-beta

- Refactor gen_from_dfn util script
- Rename hover data json file and functions
- Add CodeQL Analysis
- Add dependabot configuration
- Bump npm dependencies based on dependabot
- Group dependabot PR's for npm and gh actions
- Add ESLint for linting
- Clean-up npm scripts, pre-commit, gh workflows
- Downgrade @types/vscode to match engine.vscode
- Include keywords with comment line header in dfn
- Include keywords with blank line header in dfn
- Update demo gif
- Bump @types/node from 22.13.5 to 22.14.1 in the npm-all group
- Add lockfile check util script
- Rename bash/npm util scripts

## 0.2.0-beta

- Remove explicit json-yml language detection
- Add support for relative path filenames in go-to-def
- Add configurable file size limit to go-to-def
- Add positive test case for go-to-def
- Increase default file size limit in go-to-def
- Include specific syntax-highlighting for files
- Add script to download dfn files
- Add hover feature to show keyword description
- Fix no-hover cases and rework hover data generation
- Exclude typescript hover.json from packaging
- Update readme: summarize key features into one gif

## 0.1.0-beta

- Fix gh release workflow
- Final clean-up for beta release
- Update modflow repo org name
- Update readme for beta release
- Enable source maps for easier debugging
- Exclude unnecessary ts and test files in packaging
- Restructure gh workflow files
- Add VS Code integration tests
- Add go-to-definition feature
- Add prettier format script
- Show info message for mf6-ify command
- Fix packaging issues
- Add mf6-ify extension command to manually set language mode
- Update gh release name suffix from alpha to beta
- Add condition to release workflow
- Rework regex grammar to disregard unused keywords
- Set local pre-commit hooks to run concisely
- Add workflow trigger on push
- Update dfn files (MODFLOW 6.6.1)

## 0.0.7-alpha

- Remove workflow trigger on push
- Add workflow for publishing to VS marketplace
- Move changelog from readme.md to changelog.md
- Allow manual workflow trigger
- Enhance regex accuracy with boundary assertions
- Sort package.json
- Integrate prettier as script
- Fix regex matching
- Update dfn files (MODFLOW 6.6.0)
- Check template generation in ci
- Use python's inline script metadata

## 0.0.6-alpha

- Add gh release workflow
- Add grammar testing
- Rework workflows
- Add badges

## 0.0.5-alpha

- Lint and format with ruff, codespell and prettier
- Add pre-commit hooks
- Add ci

## 0.0.4-alpha

- Replace YAML with direct JSON template conversion
- Reduce extension file size

## 0.0.3-alpha

- Combine grammar files into one file
- Reset TextMate naming to be compatible with more themes
- Add and fix some regex patterns
- Add file icon and sample image

## 0.0.2-alpha

- Automate generation of package.json and all.tmLanugage.yaml from jinja template
- Add icon
- Add READARRAY keywords

## 0.0.1-alpha

- Alpha release
