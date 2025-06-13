from bs4 import BeautifulSoup
from typing import Dict, Any, List, Union

NOTION_COLORS = ["pink", "purple", "red", "yellow", "green", "orange", "blue", "brown", "green", "default", "gray"]


class NotionTableConverter:
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.data = dict(
            table=dict(
                database_id=self.soup.get('data-table-id'),
                headers={},
                rows=[]
            )
        )

    def extract_headers(self) -> List[Dict[str, str]]:
        """Extract headers and their Notion types from the first <tr>."""
        header_row = self.soup.find("tr")
        headers = [(th.get_text(strip=True), th.get("data-column-type", "text")) for th in header_row.find_all("th")]
        return headers

    def convert_to_notion_database_schema(self) -> List[Dict[str, Any]]:
        """Extract all rows as list of dicts with Notion property structure."""
        headers = self.extract_headers()
        rows = []

        for tr in self.soup.find_all("tr")[1:]:  # skip header row
            tds = tr.find_all("td")
            row_properties = {}

            for col_index, (col_name, col_type) in enumerate(headers):
                if len(tds) <= col_index:
                    continue
                td = tds[col_index]

                if col_type == "select":
                    select_options = [dict(name=opt.get_text(strip=True)) for opt in td.find_all("option")]
                    selected_options = [
                        opt.get_text(strip=True)
                        for opt in td.find_all("option")
                        if opt.has_attr("selected")
                    ]
                    if select_options:
                        row_properties[col_name] = {
                            "select": {"name": selected_options[0]}
                        }
                    self.convert_header(col_name, col_type, select_options)
                elif col_type == "multi_select":
                    select_options = [dict(name=opt.get_text(strip=True)) for opt in td.find_all("option")]
                    selected_options = [
                        opt.get_text(strip=True)
                        for opt in td.find_all("option")
                        if opt.has_attr("selected")
                    ]
                    if select_options:
                        row_properties[col_name] = {
                            "multi_select": [{"name": name} for name in selected_options]
                        }
                    self.convert_header(col_name, col_type, select_options)
                elif col_type == "image":
                    img = td.find("img")
                    if img:
                        file_upload_id = img.get("data-notion-file-upload-id")
                        file_name = img.get("alt")
                        if file_upload_id:
                            row_properties[col_name] = {
                                "files": [
                                    {
                                        "type": "file_upload",
                                        "name": file_name or "File",
                                        "file_upload": {"id": file_upload_id}
                                    }
                                ]
                            }
                        elif img.get("src"):
                            row_properties[col_name] = {
                                "files": [
                                    {
                                        "type": "external",
                                        "name": "Image",
                                        "external": {"url": img["src"]}
                                    }
                                ]
                            }
                    self.convert_header(col_name, col_type)
                elif col_type == "date":
                    text = td.get_text(strip=True)
                    if text:
                        row_properties[col_name] = {
                            "date": {"start": text}
                        }
                    self.convert_header(col_name, col_type)
                elif col_type == "checkbox":
                    checkbox = td.find("input", {"type": "checkbox"})
                    row_properties[col_name] = {
                        "checkbox": checkbox.has_attr("checked") if checkbox else False
                    }
                    self.convert_header(col_name, col_type)
                elif col_type == "link":
                    a = td.find("a")
                    if a and a.get("href"):
                         row_properties[col_name] = {
                             "url": a.get("href")
                         }
                    self.convert_header(col_name, col_type)
                elif col_type == "person":
                    text = td.get_text(strip=True)
                    if td.get("data-person-email"):
                        col_type = 'email'
                        row_properties[col_name] = {
                            "email": td.get("data-person-email")
                        }
                    else:
                        row_properties[col_name] = {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": text}
                                }
                            ]
                        }
                    self.convert_header(col_name, col_type)
                else:  # default: treat as rich_text
                    text = td.get_text(strip=True)
                    row_properties[col_name] = {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": text or ""}
                            }
                        ]
                    }
                    self.convert_header(col_name, col_type)
            rows.append(row_properties)
        self.data['table']["rows"] = rows
        return rows

    def convert_header(self, col_name: str, col_type: str, value: Union[Any, None] = None):
        data = None
        headers = self.data.get("table").get("headers")
        if col_type in ["select", "multi_select"]:
            options = value
            for i, option in enumerate(options):
                option["color"] = NOTION_COLORS[i % len(NOTION_COLORS)]
            data = {
                "type": col_type,
                col_type: {
                    "options": options
                }
            }
        elif col_type == "date":
            data = {"type": "date", "date": {}}
        elif col_type == "checkbox":
            data = {"type": "checkbox", "checkbox": {}}
        elif col_type == "image":
            data = {"type": "files", "files": {}}
        elif col_type == "link":
            data = {"type": "url", "url": {}}
        elif col_type == "email":
            data = {"type": "email", "email": {}}
        elif col_type == "rich_text":
            data = {"type": "rich_text", "rich_text": {}}
        else:
            data = {"type": "rich_text", "rich_text": {}}
        if not headers.get(col_name):
            self.data.get("table").get("headers")[col_name] = data
