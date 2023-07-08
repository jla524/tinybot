from typing import TypeAlias, Any
from collections import defaultdict
import requests
from dotenv import dotenv_values, find_dotenv

Json: TypeAlias = dict[str, Any]
Lines: TypeAlias = list[tuple[str, int, int]]  # filename, lines added, lines deleted
config: Json = dotenv_values(find_dotenv())

class TinyBot:
  headers = {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {config['GH_TOKEN']}", "X-GitHub-Api-Version": "2022-11-28"}

  def __init__(self, owner: str = "tinygrad", repo: str = "tinygrad", project_dir: str = "tinygrad/", user: str = "tinyb0t"):
    self.owner, self.repo, self.project_dir, self.user = owner, repo, project_dir, user
    self.base_url = f"https://api.github.com/repos/{owner}/{repo}"

  def list_prs(self) -> list[Json]:
    headers = {**self.headers, "per_page": "100"}
    response = requests.get(f"{self.base_url}/pulls", headers=headers, timeout=5, allow_redirects=True)
    assert response.status_code == 200
    return response.json()
  
  def list_pr_files(self, pr_urls: list[str]) -> dict[str, list[Json]]:
    files = {}
    headers = {**self.headers, "per_page": "100"}
    for url in pr_urls:
      response = requests.get(f"{url}/files", headers=headers, timeout=5, allow_redirects=True)
      assert response.status_code == 200
      files[url] = response.json()
    return files
  
  def get_lines(self, pr_files: dict[str, list[Json]]) -> defaultdict[str, Lines]:
    lines = defaultdict(list)
    for url, files in pr_files.items():
      n_files, total_additions, total_deletions = 0, 0, 0
      for file in files:
        if file["filename"].startswith(self.project_dir):
          additions, deletions = int(file["additions"]), int(file["deletions"])
          total_additions += additions
          total_deletions += deletions
          lines[url].append((file["filename"], additions, deletions))
          n_files += 1
      if n_files > 0:
        lines[url].append(("total", total_additions, total_deletions))
    return lines

  def _write_comment(self, lines: Lines) -> str:
    comment = f"Changes made in `{self.project_dir}`:\n"
    comment += "```\n"
    comment += "-" * 60 + "\n"
    comment += "files" + " " * 29 + "insertions       deletions\n"
    comment += "-" * 60 + "\n"
    lines_added = 0
    for fn, additions, deletions in lines:
      if fn == "total":
        lines_added = int(additions) - int(deletions)
        if len(lines) <= 2: continue
        comment += "-" * 60 + "\n"
      comment += f"{fn:<38} {additions:>5} {deletions:>15}\n"
    comment += "-" * 60 + "\n"
    comment += f"lines added in the tinygrad folder: {lines_added}\n"
    comment += "```\n"
    return comment

  def _list_my_comments(self, post_url: str) -> list[Json]:
    response = requests.get(post_url, headers=self.headers, timeout=5, allow_redirects=True)
    assert response.status_code == 200
    my_comments = []
    for comment in response.json():
      if comment["user"]["login"] == self.user:
        my_comments.append(comment)
    return my_comments

  def _delete_duplicate_comments(self, comments: list[Json]) -> None:
    for comment in comments:
      response = requests.delete(comment["url"], headers=self.headers, timeout=5, allow_redirects=True)
      assert response.status_code == 204

  def create_or_update_comments(self, pr_lines: dict[str, Lines]):
    for url, lines in pr_lines.items():
      comment = self._write_comment(lines)
      post_url = url.replace("pulls", "issues") + "/comments"
      my_comments = self._list_my_comments(post_url)
      print(post_url, "PATCH" if my_comments else "POST", len(my_comments))
      if my_comments:
        if my_comments[-1]["body"] != comment:  # if multiple comments found, use the most recent one
          response = requests.patch(my_comments[-1]["url"], json={"body": comment}, headers=self.headers, timeout=5, allow_redirects=True)
          assert response.status_code == 200
        if len(my_comments) > 1:
          self._delete_duplicate_comments(my_comments[:-1])
      else:
        response = requests.post(post_url, json={"body": comment}, headers=self.headers, timeout=5, allow_redirects=True)
        assert response.status_code == 201

if __name__ == "__main__":
  tinybot = TinyBot()
  pr_urls = [x["url"] for x in tinybot.list_prs()]
  pr_files = tinybot.list_pr_files(pr_urls)
  pr_lines = tinybot.get_lines(pr_files)
  tinybot.create_or_update_comments(pr_lines)
