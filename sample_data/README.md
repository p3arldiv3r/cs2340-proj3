# Sample data

Small, **fictional** dataset for trying out ingestion and preprocessing and for
writing tests. None of these programs are real. Replace or add to it with the
real dataset once the team chooses one.

| File | Ingestion method | What it shows |
|---|---|---|
| `programs.csv` | upload | One document per row; extra columns become metadata |
| `programs.json` | upload | List of records, same fields as the CSV |
| `book_circle.md` | upload | Whole file is one document; `# heading` becomes the title |
| `faq.txt` | upload | Plain text, includes messy whitespace and boilerplate for preprocessing to clean |
| `sample_page.html` | web | Page with nav, footer, scripts and a `<main>`; only the main text should be kept |
