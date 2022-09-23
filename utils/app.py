import uvicorn
from fastapi import FastAPI

from utils.scan_issues import scan_issue

app = FastAPI()


@app.get("/issue/{project_id}")
async def scan_project_issue(project_id: int):
    return await scan_issue(project_id)


if __name__ == '__main__':
    uvicorn.run('app:app', host='0.0.0.0', port=8008, debug=True, workers=1)
