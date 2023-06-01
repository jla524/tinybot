from typing import TypeAlias, Any, Optional
from collections import defaultdict
import requests
from dotenv import dotenv_values

Json: TypeAlias = dict[str, Any]
Lines: TypeAlias = list[tuple[str, int, int]]  # filename, lines added, lines deleted
config: Json = dotenv_values(".env")

class TinyBot:
  headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {config['GH_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
  }

  def __init__(self, owner: str = "geohot", repo: str = "tinygrad", project_dir: str = "tinygrad/"):
    self.owner, self.repo, self.project_dir = owner, repo, project_dir
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
  
  def get_lines(self, pr_files: list[Json]) -> dict[str, Lines]:
    lines = defaultdict(list)
    for url, files in pr_files.items():
      total_additions, total_deletions = 0, 0
      for file in files:
        if file["filename"].startswith(self.project_dir):
          total_additions += file["additions"]
          total_deletions += file["deletions"]
          lines[url].append((file["filename"], file["additions"], file["deletions"]))
      lines[url].append(("total", total_additions, total_deletions))
    return lines

  def comment(self, pr_lines: dict[str, Lines]):
    """
    $ curl -s -H "Authorization: token ${ACCESS_TOKEN}" \
    -X POST -d '{"body": "Your Message to Comment"}' \
    "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/issues/${PR_NUMBER}/comments"
    """
    for url, lines in pr_lines.items():
      post_url = url.replace("pulls", "issues") + "/comments"
      comment = f"Changes made in `{self.project_dir}`:\n"
      comment += "```\n"
      comment += "-" * 60 + "\n"
      comment += "files" + " " * 29 + "insertions       deletions\n"
      comment += "-" * 60 + "\n"
      for fn, additions, deletions in lines:
        if fn == "total": comment += "-" * 60 + "\n"
        comment += f"{fn:<38} {additions:>5} {deletions:>15}\n"
      comment += "```\n"
      response = requests.post(post_url, json={"body": comment}, headers=self.headers, allow_redirects=True)
      assert response.status_code == 201

if __name__ == "__main__":
  tinybot = TinyBot()
  pr_urls = [x["url"] for x in tinybot.list_prs() if x["user"]["login"] == "jla524"]  # testing
  pr_files = tinybot.list_pr_files(pr_urls)
  pr_lines = tinybot.get_lines(pr_files)
  tinybot.comment(pr_lines)
