# 我是开发者：如何添加自己项目的徽章？

### 第一次给该项目创建徽章
1. 【case/casepath.ini】文件内按模板要求更新case的的地址
2. 计算打分: `make get-score PROJECT=${你的项目名称}`
3. 符合的条目，请打[x]. 注意：因为gitlab对表格内的打勾不支持，所以需要用`<ul><li>[ ] </li></ul>`这种恶心的workaround（https://gitlab.com/gitlab-org/gitlab/-/issues/21506）
5. 提交PR
6. 将URL（`https://gitlab.daocloud.cn/ndx/qa/e2ecoverage/-/raw/main/badges/${PROJECT}.svg`）嵌入你的项目badge中

   
### 后续更新徽章

重复上述的第2到4步骤

===========================我是分隔符==================================

# Service API使用说明

### GET http://IP:PORT/
功能描述：测试接口 <Br/>
举例： curl -X GET http://127.0.0.1:8000/ <Br/>
response: <Br/>
e2e test - Hello World

### GET http://IP:PORT/projects/<keyword>
功能描述：按照字符串关键字返回查询到的gitlab项目id, name <Br/>
举例： curl -X GET http://127.0.0.1:8000/projects/insight <Br/>
response: <Br/>
{
  "715": "The Magic Insight Installer", 
  ...
  "1115": "opentelemetry-collector-insight"
}

### GET http://IP:PORT/registeredProjects
功能描述：返回当前service里已注册的所有gitlab项目 <Br/>
举例： curl -X GET http://127.0.0.1:8000/registeredProjects <Br/>
response: <Br/>
{
  "1124": "e2e-test-coverage", 
  "123": "review-bot", 
  "899": "insight"
}

### GET http://IP:PORT/project/<projectId>
功能描述：使用gitlab项目ID在本服务中注册需要统计测试自动完成率的项目 <Br/>
举例： curl -X GET http://127.0.0.1:8000/project/899 <Br/>
response: <Br/>
项目已注册，无需再次注册

### POST http://IP:PORT/project/<projectId>
功能描述：手动调此接口执行docs/test测试用例扫描及统计完成率并在badges目录下生成徽章svg文件 <Br/>
举例： curl -X POST http://127.0.0.1:8000/project/899 <Br/>
response: <Br/>
徽章已生成, 请查看本项目仓库中badges目录

### GET http://IP:PORT/issue/<projectId>
功能描述：使用gitlab项目ID获取项目issues并生成issue badges <Br/>
举例： curl -X GET http://127.0.0.1:8000/issue/899 <Br/>
response: <Br/>
Issue徽章已生成, 请查看本项目仓库中badges目录 <Br/>
说明： <Br/>
当月平均issue修复时间： average_fix_time_perMonth.svg <Br/>
未分类issue最长等待时间： earliest_issue.svg



## 使用Service制作E2E Test Coverage badge

1. 使用接口按照项目名称关键字查询项目ID，例如curl -X GET http://127.0.0.1:8000/projects/insight <Br/>
   从中找到对应的项目名称和ID <Br/>
2. 使用接口在此service中注册项目，例如url -X GET http://127.0.0.1:8000/project/<ID> <Br/>
并且初次扫描项目所有的testcase md文档完成统计并且生成徽章，例如url -X POST http://127.0.0.1:8000/project/<ID> <Br/>
备注：<Br/>
  2.1 此步骤要登陆gitlab项目并且clone代码到本地扫描所有的md文件，耗时比较长，请耐心等待 <Br/>
  2.2 gitlab经常会网络不稳定以至于请求超时；若遇到gitlab响应失败，再次请求即可 <Br/>
3. 使用Post接口扫描docs/test测试用例并计算e2e test case完成然后生成徽章，例如url -X POST http://127.0.0.1:8000/project/<ID> <Br/>
   将第3步生成的徽章url填入项目Settings - General - Badges - Badge image URL; 在项目首页即可看到；并且填入项目docs/test/README.md文件中即可展示测试用例详细完成率

# schedule job
此service在gitlab CI中定时将已注册项目扫描生成新的完成率统计，徽章数据会随之更新

# 启动service
docker run -d --name e2e-test-coverage-service -p 8000:8000 --restart always release-ci.daocloud.io/common-ci/e2e-test-coverage-service:v0.0.0