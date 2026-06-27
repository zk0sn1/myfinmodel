# Offline Instructions for Sharing the Excel Workbook

Best approach: **put the workbook in the repo and pair it with a written spec**, rather than relying on the `.xlsx` alone.

## Recommended approach

1. **Set up git locally** for this repo.
   - You’ll want version history for code and requirements.
   - Even if the workbook is temporary, keeping it in the repo makes it easy to reference.

2. **Commit the Excel workbook to a `docs/` or `specs/` folder**.
   - Example: `docs/retirement-model-spec.xlsx`
   - This is fine if the file is reasonably small and not sensitive.

3. **Also add a Markdown summary of the workbook**.
   - Example: `docs/model-spec.md`
   - Include:
     - which sheets exist
     - what each sheet means
     - required inputs
     - formulas/rules that matter
     - expected outputs
     - any scenario logic / guardrail rules
   - This is important because Excel is hard to diff and harder to interpret precisely.

4. **If specific sheets are critical, export them too**:
   - tables → `.csv`
   - narrative instructions → `.md`
   - formulas / assumptions → `.md` or `.csv`

## Suggested repo structure

```text
docs/
  retirement-model-spec.xlsx
  model-spec.md
  inputs-sheet.csv
  assumptions-sheet.csv
  expected-results-sheet.csv
```

## When to keep Excel vs convert it

### Keep as Excel if:
- formatting matters
- there are multiple sheets
- formulas and examples are useful context

### Convert parts to CSV/Markdown if:
- you want the implementation to follow exact tabular data
- you want cleaner diffs in git
- you want easier parsing later

## Practical guidance

If the workbook contains:
- **instructions/explanations** → copy those into Markdown
- **input tables** → export as CSV
- **expected outputs/sample results** → export as CSV
- **complex formulas/business rules** → describe them in Markdown in plain English

## Local git workflow

If you haven’t already set up the repo locally, a simple flow is:

```bash
git clone git@github.com:Blockish/myfinmodel.git
cd myfinmodel
git checkout -b workbook-spec
mkdir -p docs
# add workbook and exported files
git add docs
git commit -m "Add workbook-based simulation specification"
git push -u origin workbook-spec
```

Then open a pull request.

## What not to do

- Don’t rely on screenshots alone.
- Don’t only describe the workbook in chat if it’s detailed and multi-sheet.
- Don’t convert everything to JSON unless the app actually needs machine-readable config.

## Best overall answer

**Do both**:
- keep the original Excel workbook in the repo
- and create a concise Markdown + CSV extraction of the important parts

That gives you:
- human-readable requirements
- version control
- easier implementation
- and a durable source of truth
