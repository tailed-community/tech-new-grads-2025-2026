import requests
import json
import datetime
import shutil
import os

def scrape_newgrads():
    existing_data = []
    try:
        with open("data/current.json", "r", encoding='utf-8') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        pass

    url = "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/refs/heads/dev/.github/scripts/listings.json"
    response = requests.get(url)
    data = response.json()

    def normalize_item(item):
        return {
            "category": item.get("category", ""),
            "company_name": item.get("company_name", ""),
            "id": item.get("id", ""),
            "title": item.get("title", ""),
            "active": item.get("active", False),
            "date_updated": item.get("date_updated"),
            "date_posted": item.get("date_posted"),
            "url": item.get("url", ""),
            "locations": item.get("locations", []),
            "degrees": item.get("degrees", [])
        }

    # Load archived data
    archived_data = {}
    try:
        with open("data/archived.json", "r", encoding='utf-8') as f:
            for item in json.load(f):
                normalized = normalize_item(item)
                archived_data[normalized['id']] = normalized
    except FileNotFoundError:
        pass

    # Merge all new data into archived
    for item in data:
        normalized = normalize_item(item)
        archived_data[normalized['id']] = normalized

    # Save merged archived data
    with open("data/archived.json", "w", encoding='utf-8') as f:
        json.dump(list(archived_data.values()), f, indent=4, ensure_ascii=False)

    filtered_data = []
    for item in data:
        if item.get("active") and item.get("active") == True:
            filtered_item = {
                "category": item.get("category"),
                "company_name": item.get("company_name"),
                "id": item.get("id"),
                "title": item.get("title"),
                "active": item.get("active"),
                "date_updated": item.get("date_updated"),
                "date_posted": item.get("date_posted"),
                "url": item.get("url"),
                "locations": item.get("locations"),
                "degrees": item.get("degrees")
            }
            filtered_data.append(filtered_item)

    # Sort by terms most recent to most future
    filtered_data.sort(key=lambda item: (item.get("date_posted", 0), item.get("title", "")), reverse=True)

    # Compare with existing data for logging
    existing_ids = set(item['id'] for item in existing_data)
    new_ids = set(item['id'] for item in filtered_data)
    added_ids = new_ids - existing_ids
    removed_ids = existing_ids - new_ids

    print(f"Total opportunities: {len(data)}")
    print(f"Total active opportunities: {len(filtered_data)}")
    print(f"Total added: {len(added_ids)}")
    print(f"Total removed: {len(removed_ids)}")

    # Save filtered data to JSON
    with open("data/current.json", "w", encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=4, ensure_ascii=False)

    # Generate markdown table
    table_rows = []
    for item in filtered_data:
        company = item["company_name"]
        role = item["title"]
        locations = ", ".join(item["locations"]) if item["locations"] else ""
        deadline = datetime.datetime.fromtimestamp(item["date_posted"]).strftime('%Y-%m-%d') if item["date_posted"] else ""
        link = f"[Apply Here]({item['url']})"
        table_rows.append(f"| {company} | {role} | {locations} | {deadline} | {link} |")

    # Update README.md
    readme_path = "README.md"
    with open(readme_path, "r", encoding='utf-8') as f:
        content = f.read()

    new_rows = "\n".join(table_rows)

    # Find the table section
    table_marker = "## New Grad Job Opportunities"
    table_start = content.find(table_marker)
    if table_start == -1:
        print("Table section not found in README")
        return

    # Find the header line
    header_line = "| Company | Role | Location | Date Posted | Link |"
    header_pos = content.find(header_line, table_start)
    if header_pos == -1:
        print("Table header not found")
        return

    # Find the separator line
    separator_line = "| ------- | ---- | -------- | ----------- | ---- |"
    separator_pos = content.find(separator_line, header_pos)
    if separator_pos == -1:
        print("Table separator not found")
        return

    # Start of rows (after separator)
    rows_start = separator_pos + len(separator_line) + 1  # +1 for \n

    # Find the end of the table (next section or end)
    next_section_pos = content.find("##", rows_start)
    if next_section_pos == -1:
        next_section_pos = len(content)

    # Replace the rows
    new_content = content[:rows_start] + new_rows + "\n" + content[next_section_pos:]

    with open(readme_path, "w", encoding='utf-8') as f:
        f.write(new_content)

if __name__ == "__main__":
    scrape_newgrads()
