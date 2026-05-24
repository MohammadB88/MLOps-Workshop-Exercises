# Documentation Tooling Recommendations

## Zensical

Research suggests Zensical is not a widely recognized documentation tool. The name may refer to an internal tool or a less common platform.

## Recommended Alternatives

For MkDocs-based projects like this workshop, consider these documentation enhancement tools:

### 1. MkDocs Material Insiders
- **What it does**: Provides additional features for the Material theme including better search, diagrams, and social cards
- **Best for**: Teams that already use MkDocs Material and want premium features
- **Cost**: Sponsorware (paid sponsor gets access)

### 2. Diátaxis Framework
- **What it does**: A systematic approach to documentation structure (tutorials, how-to guides, reference, explanation)
- **Best for**: Organizing documentation content into clear user-centric categories
- **Cost**: Free

### 3. Vale / write-good
- **What it does**: Prose linters that check documentation for grammar, style, and consistency issues
- **Best for**: Maintaining consistent terminology and writing quality
- **Cost**: Free, open-source

### 4. Docsify / Docusaurus
- **What it does**: Alternative documentation site generators with built-in versioning and search
- **Best for**: Projects that need versioned documentation or React-based customization
- **Cost**: Free, open-source

### 5. Read the Docs
- **What it does**: Hosted documentation platform with versioning, search, and analytics
- **Best for**: Open-source projects that want automatic builds and hosting
- **Cost**: Free for open-source, paid for private

## Recommendation

For this workshop, **MkDocs Material** (already in use) combined with **Diátaxis** content structuring and **Vale** for prose linting provides the best value. Adding Vale as a pre-commit hook would enforce terminology consistency automatically.

No changes to the current MkDocs setup are recommended unless the team wants versioned documentation, in which case migrating to Read the Docs is the simplest path forward.
