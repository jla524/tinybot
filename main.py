from typing import TypeAlias, Any, Optional
from collections import defaultdict
import requests
from dotenv import dotenv_values

Json: TypeAlias = dict[str, Any]
config: Json = dotenv_values(".env")

class TinyBot:
  headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {config['GH_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
  }

  def __init__(self, owner: str = "geohot", repo: str = "tinygrad"):
    self.owner, self.repo = owner, repo
    self.base_url = f"https://api.github.com/repos/{owner}/{repo}"

  def list_prs(self) -> Json:
    response = requests.get(f"{self.base_url}/pulls", headers=self.headers, allow_redirects=True)
    assert response.status_code == 200
    return response.json()
  
  def list_pr_files(self, pr_urls: list[str]) -> dict[str, Json]:
    files = {}
    for url in pr_urls:
      response = requests.get(f"{url}/files", headers=self.headers, allow_redirects=True)
      assert response.status_code == 200
      files[url] = response.json()
    return files
  
  def get_lines(self, pr_files: list[Json], file_start: str = "tinygrad/") -> dict[str, tuple[str, int, int]]:
    lines = defaultdict(list)
    for url, files in pr_files.items():
      for file in files:
        if file["filename"].startswith(file_start):
          lines[url].append((file["filename"], file["additions"], file["deletions"]))
    return lines

if __name__ == "__main__":
  tinybot = TinyBot()
  pr_urls = [x["url"] for x in tinybot.list_prs()]
  pr_files = tinybot.list_pr_files(pr_urls)
  for url, files in tinybot.get_lines(pr_files).items():
    print(url)
    for fn, added, deleted in files:
      print(f"{fn}\tadded {added}\tdeleted {deleted}")
    print()