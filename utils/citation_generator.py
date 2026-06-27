import csv
import io

def generate_apa(paper):
    authors = paper.get('authors', [])
    year = paper.get('year', 'n.d.')
    title = paper.get('title', 'No Title')
    source = paper.get('source', 'Unknown Source')
    
    if not authors:
        author_str = "Unknown Author."
    elif len(authors) == 1:
        author_str = f"{authors[0]}."
    elif len(authors) == 2:
        author_str = f"{authors[0]} & {authors[1]}."
    else:
        author_str = f"{authors[0]} et al."
        
    return f"{author_str} ({year}). {title}. {source}."

def generate_bibtex(papers):
    bibtex_str = ""
    for i, paper in enumerate(papers):
        authors = paper.get('authors', [])
        year = paper.get('year', 'n.d.')
        title = paper.get('title', 'No Title')
        
        author_str = " and ".join(authors) if authors else "Unknown"
        
        bib_id = f"paper{i}_{year}"
        if authors:
            # try to use the last name of the first author
            bib_id = f"{authors[0].split()[-1].lower()}{year}"
            
        bibtex_str += f"@article{{{bib_id},\n"
        bibtex_str += f"  title={{{title}}},\n"
        bibtex_str += f"  author={{{author_str}}},\n"
        bibtex_str += f"  year={{{year}}}\n"
        bibtex_str += "}\n\n"
    return bibtex_str

def generate_csv(papers):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Authors', 'Year', 'Source', 'Citations', 'Abstract'])
    
    for paper in papers:
        writer.writerow([
            paper.get('title', ''),
            ", ".join(paper.get('authors', [])),
            paper.get('year', ''),
            paper.get('source', ''),
            paper.get('citations', 0),
            paper.get('abstract', '')
        ])
    return output.getvalue()
