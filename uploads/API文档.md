# 智能典籍书屋 — API/接口文档

> 项目：library-management（智典书屋）
> 后端：Java 17 / Spring Boot 2.7 / MyBatis-Plus
> 基础路径：`/api`
> 生成日期：2026-04-30

---

## 目录

1. [通用约定](#1-通用约定)
2. [认证模块 /auth](#2-认证模块-auth)
3. [用户模块 /users](#3-用户模块-users)
4. [图书模块 /books](#4-图书模块-books)
5. [借阅模块 /borrow](#5-借阅模块-borrow)
6. [分类模块 /category](#6-分类模块-category)
7. [评论模块 /comments](#7-评论模块-comments)
8. [预约模块 /reservation](#8-预约模块-reservation)
9. [公告模块 /notice](#9-公告模块-notice)
10. [数字资源模块 /digital-resource](#10-数字资源模块-digital-resource)
11. [统计模块 /statistics](#11-统计模块-statistics)
12. [系统配置 /config](#12-系统配置-config)
13. [文件上传 /upload](#13-文件上传-upload)
14. [AI模块 /ai](#14-ai模块-ai)
15. [管理员模块 /admin](#15-管理员模块-admin)
16. [测试模块 /test](#16-测试模块-test)
17. [数据模型参考](#17-数据模型参考)
18. [错误码参考](#18-错误码参考)

---

## 1. 通用约定

### 1.1 请求格式

| 项目 | 说明 |
|------|------|
| Content-Type | `application/json`（上传接口为 `multipart/form-data`） |
| 字符编码 | UTF-8 |
| 基础路径 | `/api` |

### 1.2 认证方式

```
Authorization: Bearer <jwt_token>
```

- 登录成功后返回 JWT token
- Token 包含 claims：`userId`、`username`、`role`
- 公开接口无需携带 token（见各接口标注）

### 1.3 角色定义

| role 值 | 含义 | 权限 |
|---------|------|------|
| `0` | 管理员 | 全部权限 |
| `1` | 普通用户 | 用户端权限 |

### 1.4 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | Integer | 200=成功，其他=失败 |
| `message` | String | 提示信息 |
| `data` | Object/Array/null | 响应数据 |

### 1.5 分页响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "records": [ ... ]
  }
}
```

---

## 2. 认证模块 /auth

### 2.1 登录

```
POST /api/auth/login
```

**权限**：公开

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | String | 是 | 用户名 |
| password | String | 是 | 密码，6-20位 |
| role | String | 是 | 角色："0"=管理员，"1"=用户 |

**请求示例**：
```json
{
  "username": "admin",
  "password": "123456",
  "role": "0"
}
```

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiJ9...",
    "userId": 1,
    "user": {
      "id": 1,
      "username": "admin",
      "realName": "管理员",
      "phone": "13800138000",
      "email": "admin@library.com",
      "role": 0,
      "status": 1,
      "avatar": null
    }
  }
}
```

---

### 2.2 注册

```
POST /api/auth/register
```

**权限**：公开

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | String | 是 | 用户名，3-20位 |
| password | String | 是 | 密码，6-20位 |
| confirmPassword | String | 是 | 确认密码 |
| realName | String | 是 | 真实姓名 |
| phone | String | 否 | 联系电话 |
| email | String | 否 | 邮箱 |
| role | String | 是 | 角色 |

**请求示例**：
```json
{
  "username": "reader01",
  "password": "reader123",
  "confirmPassword": "reader123",
  "realName": "张三",
  "phone": "13912345678",
  "email": "zhangsan@example.com",
  "role": "1"
}
```

**响应示例**：
```json
{
  "code": 200,
  "message": "注册成功",
  "data": null
}
```

---

### 2.3 退出登录

```
POST /api/auth/logout
```

**权限**：公开（携带 token）

**请求头**：`Authorization: Bearer <token>`

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

---

## 3. 用户模块 /users

### 3.1 获取用户列表（管理员）

```
GET /api/users
```

**权限**：管理员

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "username": "admin",
      "realName": "管理员",
      "phone": "13800138000",
      "email": "admin@library.com",
      "role": 0,
      "status": 1,
      "avatar": null,
      "createTime": "2025-01-01T00:00:00",
      "lastLoginTime": "2026-04-30"
    }
  ]
}
```

---

### 3.2 获取个人信息

```
GET /api/users/profile
```

**权限**：需认证

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "username": "admin",
    "realName": "管理员",
    "phone": "13800138000",
    "email": "admin@library.com",
    "role": 0,
    "status": 1,
    "avatar": "/images/userimages/avatar_1.png"
  }
}
```

---

### 3.3 修改个人信息

```
PUT /api/users/profile
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| realName | String | 否 | 真实姓名 |
| email | String | 否 | 邮箱 |
| phone | String | 否 | 电话 |
| avatar | String | 否 | 头像路径 |

**请求示例**：
```json
{
  "realName": "张三丰",
  "email": "zsf@example.com",
  "phone": "13900001111",
  "avatar": "/images/userimages/avatar_2.png"
}
```

---

### 3.4 修改密码

```
PUT /api/users/password
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| password | String | 是 | 新密码 |

**请求示例**：
```json
{
  "password": "newpassword123"
}
```

---

### 3.5 新增用户（管理员）

```
POST /api/users
```

**权限**：管理员

**请求体**：User 实体（部分字段）

```json
{
  "username": "reader02",
  "password": "reader456",
  "realName": "李四",
  "phone": "13600001111",
  "role": 1
}
```

---

### 3.6 修改用户（管理员）

```
PUT /api/users/{id}
```

**权限**：管理员

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| id | Path | Long | 用户ID |

**请求体**：User 实体（修改的字段）

---

### 3.7 删除用户（管理员）

```
DELETE /api/users/{id}
```

**权限**：管理员

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| id | Path | Long | 用户ID |

---

### 3.8 修改用户状态（管理员）

```
PUT /api/users/{id}/status
```

**权限**：管理员

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| id | Path | Long | 用户ID |
| status | Query | Integer | 0=禁用，1=启用 |

---

## 4. 图书模块 /books

### 4.1 搜索/列表图书

```
GET /api/books
```

**权限**：公开

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| keyword | String | — | 搜索关键词（书名/作者/ISBN） |
| category | String | — | 分类名称 |
| page | Integer | 1 | 页码 |
| pageSize | Integer | 10 | 每页条数 |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 25,
    "records": [
      {
        "id": 1,
        "isbn": "978-7-111-00001",
        "title": "三体",
        "author": "刘慈欣",
        "publisher": "重庆出版社",
        "publishDate": "2008-01-01",
        "category": "文学",
        "coverUrl": "/images/bookimages/cover_1.jpg",
        "description": "中国科幻文学的里程碑之作...",
        "totalStock": 10,
        "availableStock": 7,
        "location": "A-01-03"
      }
    ]
  }
}
```

---

### 4.2 获取图书详情

```
GET /api/books/{id}
```

**权限**：公开

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| id | Path | Long | 图书ID |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "isbn": "978-7-111-00001",
    "title": "三体",
    "author": "刘慈欣",
    "publisher": "重庆出版社",
    "publishDate": "2008-01-01",
    "category": "文学",
    "coverUrl": "/images/bookimages/cover_1.jpg",
    "description": "中国科幻文学的里程碑之作...",
    "totalStock": 10,
    "availableStock": 7,
    "location": "A-01-03"
  }
}
```

---

### 4.3 新增图书（管理员）

```
POST /api/books
```

**权限**：管理员

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| isbn | String | 是 | ISBN |
| title | String | 是 | 书名 |
| author | String | 是 | 作者 |
| publisher | String | 否 | 出版社 |
| publishDate | String | 否 | 出版日期 |
| category | String | 否 | 分类名称 |
| coverUrl | String | 否 | 封面图路径 |
| description | String | 否 | 简介 |
| totalStock | Integer | 是 | 总库存 |
| location | String | 否 | 馆藏位置 |

---

### 4.4 修改图书（管理员）

```
PUT /api/books/{id}
```

**权限**：管理员

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| id | Path | Long | 图书ID |

**请求体**：同 [4.3 新增图书]

---

### 4.5 删除图书（管理员）

```
DELETE /api/books/{id}
```

**权限**：管理员

---

### 4.6 获取分类列表

```
GET /api/books/categories
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": ["文学", "科技", "历史", "哲学", "计算机"]
}
```

---

### 4.7 获取推荐图书

```
GET /api/books/recommended
```

**权限**：公开

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | Integer | 8 | 返回数量（上限100） |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "id": 1, "title": "三体", "coverUrl": "...", ... }
  ]
}
```

---

## 5. 借阅模块 /borrow

### 5.1 借阅图书

```
POST /api/borrow
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bookId | Long | 是 | 图书ID |

**请求示例**：
```json
{
  "bookId": 1
}
```

**响应示例**：
```json
{
  "code": 200,
  "message": "借阅成功",
  "data": {
    "id": 100,
    "userId": 2,
    "bookId": 1,
    "bookTitle": "三体",
    "borrowCode": "B20260430001",
    "borrowDate": "2026-04-30T10:30:00",
    "dueDate": "2026-05-30T10:30:00",
    "status": 0,
    "renewCount": 0,
    "overdueFine": 0
  }
}
```

---

### 5.2 归还图书

```
PUT /api/borrow/{recordId}/return
```

**权限**：需认证

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| recordId | Path | Long | 借阅记录ID |

---

### 5.3 续借

```
PUT /api/borrow/{recordId}/renew
```

**权限**：需认证

| 参数 | 位置 | 类型 | 说明 |
|------|------|------|------|
| recordId | Path | Long | 借阅记录ID |

---

### 5.4 我的借阅记录

```
GET /api/borrow/records
```

**权限**：需认证

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 100,
      "userId": 2,
      "bookId": 1,
      "bookTitle": "三体",
      "userName": "张三",
      "borrowCode": "B20260430001",
      "borrowDate": "2026-04-30T10:30:00",
      "dueDate": "2026-05-30T10:30:00",
      "returnDate": null,
      "status": 0,
      "renewCount": 0,
      "overdueFine": 0
    }
  ]
}
```

---

### 5.5 逾期记录

```
GET /api/borrow/overdue
```

**权限**：需认证

---

### 5.6 借阅统计（用户）

```
GET /api/borrow/stats
```

**权限**：需认证

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "borrowingCount": 2,
    "returnedCount": 15,
    "overdueCount": 0
  }
}
```

---

### 5.7 借阅统计（管理员）

```
GET /api/borrow/admin/stats
```

**权限**：管理员

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "books": 500,
    "users": 120,
    "borrows": 350,
    "overdue": 5,
    "booksGrowth": 12.5,
    "usersGrowth": 8.3,
    "borrowsGrowth": 15.2,
    "overdueGrowth": -20.0
  }
}
```

---

### 5.8 借阅趋势（近7天）

```
GET /api/borrow/trend
```

**权限**：需认证

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "date": "2026-04-24", "count": 15 },
    { "date": "2026-04-25", "count": 22 },
    { "date": "2026-04-26", "count": 18 }
  ]
}
```

---

### 5.9 热门图书

```
GET /api/borrow/hot-books
```

**权限**：需认证

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| limit | Integer | 10 | 返回数量（上限100） |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "title": "三体", "count": 45 },
    { "title": "活着", "count": 38 }
  ]
}
```

---

### 5.10 删除借阅记录

```
DELETE /api/borrow/record/{recordId}
```

**权限**：需认证

---

## 6. 分类模块 /category

### 6.1 分类列表

```
GET /api/api/category/list
```

> 注意：该路径包含两层 `/api`，因为后端 context-path 为 `/api`，而路由映射为 `/api/category`

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "name": "文学",
      "parentId": null,
      "sort": 1,
      "bookCount": 45
    },
    {
      "id": 4,
      "name": "小说",
      "parentId": 1,
      "sort": 1,
      "bookCount": 20
    }
  ]
}
```

---

### 6.2 分类详情

```
GET /api/api/category/{id}
```

**权限**：公开

---

### 6.3 新增分类（管理员）

```
POST /api/api/category
```

**权限**：管理员

**请求体**：
```json
{
  "name": "心理学",
  "parentId": null,
  "sort": 10
}
```

---

### 6.4 修改分类（管理员）

```
PUT /api/api/category
```

**权限**：管理员

---

### 6.5 删除分类（管理员）

```
DELETE /api/api/category/{id}
```

**权限**：管理员

---

### 6.6 分类下的图书

```
GET /api/api/category/{id}/books
```

**权限**：公开

---

## 7. 评论模块 /comments

### 7.1 发表评论

```
POST /api/comments
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bookId | Long | 是 | 图书ID |
| rating | Integer | 否 | 评分，1-5 |
| content | String | 是 | 评论内容 |
| parentId | Long | 否 | 父评论ID（回复时使用） |

**请求示例**：
```json
{
  "bookId": 1,
  "rating": 5,
  "content": "非常好看，推荐！",
  "parentId": null
}
```

---

### 7.2 获取图书评论列表

```
GET /api/comments/book/{bookId}
```

**权限**：公开（可选认证：若携带 token 则返回当前用户的点赞状态）

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 10,
      "bookId": 1,
      "userId": 2,
      "username": "张三",
      "userAvatar": "/images/userimages/avatar_1.png",
      "rating": 5,
      "content": "非常好看，推荐！",
      "likeCount": 3,
      "replyCount": 1,
      "parentId": null,
      "isLiked": true,
      "createTime": "2026-04-30 10:30"
    }
  ]
}
```

---

### 7.3 获取图书评分汇总

```
GET /api/comments/book/{bookId}/rating
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "averageRating": 4.5,
    "totalComments": 28,
    "rating5": 15,
    "rating4": 8,
    "rating3": 3,
    "rating2": 1,
    "rating1": 1
  }
}
```

---

### 7.4 点赞评论

```
POST /api/comments/{commentId}/like
```

**权限**：需认证

---

### 7.5 取消点赞

```
DELETE /api/comments/{commentId}/like
```

**权限**：需认证

---

## 8. 预约模块 /reservation

### 8.1 预约图书

```
POST /api/reservation
```

或

```
POST /api/reservation/reserve
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| bookId | Long | 是 | 图书ID |
| expireDate | String | 否 | 预约到期日期 |

**请求示例**：
```json
{
  "bookId": 1,
  "expireDate": "2026-05-07"
}
```

---

### 8.2 取消预约

```
DELETE /api/reservation/{reservationId}
```

或

```
PUT /api/reservation/cancel/{reservationId}
```

**权限**：需认证（仅限自己的预约）

---

### 8.3 我的预约列表

```
GET /api/reservation/list
```

**权限**：需认证

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 5,
      "userId": 2,
      "bookId": 1,
      "bookTitle": "三体",
      "userName": "张三",
      "reserveDate": "2026-04-30T10:00:00",
      "expireDate": "2026-05-07T10:00:00",
      "status": 0,
      "notified": false
    }
  ]
}
```

**status 状态说明**：

| 值 | 含义 |
|----|------|
| 0 | 等待中 |
| 1 | 可取书 |
| 2 | 已取消 |
| 3 | 已完成 |

---

### 8.4 我的预约数量

```
GET /api/reservation/count
```

**权限**：需认证

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": 3
}
```

---

### 8.5 预约列表（管理员）

```
GET /api/reservation/admin/list
```

**权限**：管理员

---

### 8.6 完成预约（管理员）

```
PUT /api/reservation/admin/complete/{reservationId}
```

**权限**：管理员

---

## 9. 公告模块 /notice

### 9.1 公告列表（用户端）

```
GET /api/notice/list
```

**权限**：公开

**请求参数**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | Integer | 1 | 页码 |
| pageSize | Integer | 10 | 每页条数 |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 20,
    "records": [
      {
        "id": 1,
        "title": "五一假期开放时间调整通知",
        "summary": "五一期间图书馆开放时间调整如下...",
        "publishDate": "2026-04-28",
        "isImportant": true
      }
    ]
  }
}
```

---

### 9.2 公告详情

```
GET /api/notice/{id}
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "title": "五一假期开放时间调整通知",
    "content": "<p>各位读者：</p><p>五一期间图书馆开放时间调整如下...</p>",
    "publishDate": "2026-04-28",
    "isImportant": true
  }
}
```

---

### 9.3 公告分页（管理员）

```
GET /api/notice/page
```

**权限**：管理员

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | Integer | 1 | 页码 |
| size | Integer | 10 | 每页条数 |
| title | String | — | 标题搜索（可选） |

---

### 9.4 新增公告（管理员）

```
POST /api/notice
```

**权限**：管理员

**请求体**：
```json
{
  "title": "新书上架通知",
  "summary": "本月新增图书200册...",
  "content": "<p>详细内容...</p>",
  "publishDate": "2026-04-30",
  "isImportant": false,
  "isActive": true
}
```

---

### 9.5 修改公告（管理员）

```
PUT /api/notice
```

**权限**：管理员

---

### 9.6 删除公告（管理员）

```
DELETE /api/notice/{id}
```

**权限**：管理员

---

## 10. 数字资源模块 /digital-resource

### 10.1 按分类获取数字资源

```
GET /api/digital-resource/list/{category}
```

**权限**：公开

| 参数 | 位置 | 说明 |
|------|------|------|
| category | Path | ebook / journal / media / database |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": 1,
      "category": "ebook",
      "name": "三体（电子书）",
      "description": "刘慈欣科幻巨著电子版",
      "url": "https://example.com/ebook/santi",
      "available": true,
      "sortOrder": 1
    }
  ]
}
```

---

### 10.2 获取资源分类列表

```
GET /api/digital-resource/categories
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": ["ebook", "journal", "media", "database"]
}
```

---

### 10.3 资源分页（管理员）

```
GET /api/digital-resource/page
```

**权限**：管理员

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | Integer | 1 | 页码 |
| size | Integer | 10 | 每页条数 |
| keyword | String | — | 关键词搜索 |
| category | String | — | 分类筛选 |

---

### 10.4 新增数字资源（管理员）

```
POST /api/digital-resource
```

**权限**：管理员

**请求体**：
```json
{
  "category": "ebook",
  "name": "三体（电子书）",
  "description": "刘慈欣科幻巨著电子版",
  "url": "https://example.com/ebook/santi",
  "available": true,
  "sortOrder": 1
}
```

---

### 10.5 修改数字资源（管理员）

```
PUT /api/digital-resource
```

**权限**：管理员

---

### 10.6 删除数字资源（管理员）

```
DELETE /api/digital-resource/{id}
```

**权限**：管理员

---

## 11. 统计模块 /statistics

### 11.1 获取统计数据总览

```
GET /api/api/statistics
```

或

```
GET /api/api/statistics/dashboard
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "totalBooks": 500,
    "totalUsers": 120,
    "totalBorrows": 350,
    "overdueCount": 5,
    "booksGrowth": 12.5,
    "usersGrowth": 8.3,
    "borrowsGrowth": 15.2,
    "overdueGrowth": -20.0,
    "borrowTrend": [
      { "date": "2026-04-24", "count": 15 },
      { "date": "2026-04-25", "count": 22 }
    ],
    "hotBooks": [
      { "title": "三体", "count": 45 }
    ],
    "categoryDistribution": [
      { "name": "文学", "value": 150 },
      { "name": "科技", "value": 120 }
    ]
  }
}
```

---

### 11.2 借阅趋势

```
GET /api/api/statistics/borrow-trend
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "date": "2026-04-24", "count": 15 },
    { "date": "2026-04-25", "count": 22 }
  ]
}
```

---

## 12. 系统配置 /config

### 12.1 获取所有配置

```
GET /api/config
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "library_name": "智能典籍书屋",
    "library_address": "XX市XX区XX路100号",
    "borrow_limit": "5",
    "borrow_days": "30",
    "overdue_fine_per_day": "0.5"
  }
}
```

---

### 12.2 更新配置（管理员）

```
PUT /api/config
```

**权限**：管理员

**请求体**：
```json
{
  "library_name": "智能典籍书屋（旗舰馆）",
  "borrow_limit": "10",
  "borrow_days": "45"
}
```

---

## 13. 文件上传 /upload

### 13.1 上传图片

```
POST /api/upload/image
```

**权限**：公开

**Content-Type**：`multipart/form-data`

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | 图片文件 |
| type | String | 否 | book=图书封面，user=用户头像（默认book） |

**响应示例**：
```json
{
  "code": 200,
  "message": "上传成功",
  "data": "/images/bookimages/cover_20260430120000.jpg"
}
```

---

### 13.2 删除图片

```
DELETE /api/upload/image
```

**权限**：公开

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| url | String | 是 | 图片路径 |

---

## 14. AI模块 /ai

### 14.1 AI健康检查

```
GET /api/ai/health
```

**权限**：公开

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "enabled": true,
    "provider": "deepseek",
    "model": "deepseek-chat",
    "hasApiKey": true,
    "features": {
      "chat": true,
      "recommendation": true,
      "summary": true,
      "sentiment": true,
      "digest": true
    }
  }
}
```

---

### 14.2 AI对话

```
POST /api/ai/chat
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | String | 是 | 用户提问 |
| context | Map | 否 | 上下文信息 |

**请求示例**：
```json
{
  "question": "借书可以借多久？",
  "context": { "bookId": 1 }
}
```

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "answer": "普通图书借阅期限为30天，到期前可续借一次，续借期限为15天。",
    "usage": { "promptTokens": 50, "completionTokens": 30 },
    "model": "deepseek-chat",
    "fallback": false
  }
}
```

---

### 14.3 AI图书推荐

```
GET /api/ai/recommend
```

**权限**：需认证

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| userId | Long | — | 用户ID |
| limit | Integer | 6 | 推荐数量 |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "books": [
      { "id": 5, "title": "球状闪电", "author": "刘慈欣", ... }
    ],
    "message": "根据您的借阅历史为您推荐以下图书",
    "model": "deepseek-chat",
    "fallback": false
  }
}
```

---

### 14.4 AI相似图书

```
GET /api/ai/similar
```

**权限**：需认证

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| bookId | Long | 是 | 参考图书ID |
| limit | Integer | 4 | 返回数量 |

---

### 14.5 AI摘要生成

```
POST /api/ai/summary
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | String | 是 | 待摘要的文本内容 |

**请求示例**：
```json
{
  "content": "《三体》是刘慈欣创作的系列长篇科幻小说..."
}
```

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "summary": "《三体》是刘慈欣的科幻巨著，讲述人类文明与三体文明的首次接触...",
    "model": "deepseek-chat",
    "fallback": false
  }
}
```

---

### 14.6 情感分析

```
POST /api/ai/sentiment
```

**权限**：需认证

**请求体**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| text | String | 是 | 待分析的文本 |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "label": "positive",
    "score": 0.92,
    "fallback": false
  }
}
```

---

### 14.7 AI精读摘要

```
POST /api/ai/digest
```

**权限**：需认证

**Content-Type**：`multipart/form-data`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| content | String | 是 | 要分析的内容 |
| image | File | 否 | 相关图片 |
| depth | String | 否 | 分析深度：detailed / brief（默认 detailed） |
| style | String | 否 | 风格：popular / academic（默认 popular） |

**响应示例**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "summary": "本文主要探讨了...",
    "keyPoints": ["要点1", "要点2", "要点3"],
    "appreciation": "这篇文章的艺术特色在于...",
    "conclusion": "综上所述...",
    "fallback": false
  }
}
```

---

## 15. 管理员模块 /admin

### 15.1 重置演示数据

```
POST /api/api/admin/reset-demo
```

**权限**：管理员

**响应示例**：
```json
{
  "code": 200,
  "message": "演示数据已重置",
  "data": {
    "booksDeleted": 15,
    "usersDeleted": 5,
    "presetsDeleted": 3,
    "message": "演示数据已成功重置"
  }
}
```

---

## 16. 测试模块 /test

### 16.1 Hello

```
GET /api/test/hello
```

**权限**：公开

**响应**（text/plain）：
```
Hello, Library Management System!
```

---

### 16.2 健康检查

```
GET /api/test/health
```

**权限**：公开

**响应示例**：
```json
{
  "status": "UP"
}
```

---

## 17. 数据模型参考

### 17.1 用户（User）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| username | String | 用户名（唯一） |
| password | String | 密码（BCrypt加密） |
| realName | String | 真实姓名 |
| phone | String | 联系电话 |
| email | String | 邮箱 |
| role | Integer | 0=管理员，1=用户 |
| status | Integer | 0=禁用，1=启用 |
| avatar | String | 头像路径 |
| lastLoginTime | LocalDate | 最后登录日期 |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |
| deleted | Integer | 逻辑删除：0=正常，1=已删除 |

### 17.2 图书（Book）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| isbn | String | ISBN（唯一） |
| title | String | 书名 |
| author | String | 作者 |
| publisher | String | 出版社 |
| publishDate | String | 出版日期 |
| categoryId | Long | 分类ID |
| category | String | 分类名称（瞬时字段） |
| coverUrl | String | 封面图URL |
| description | String | 简介 |
| totalStock | Integer | 总库存 |
| availableStock | Integer | 可借库存 |
| location | String | 馆藏位置 |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |
| deleted | Integer | 逻辑删除 |

### 17.3 借阅记录（BorrowRecord）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| userId | Long | 用户ID |
| bookId | Long | 图书ID |
| bookTitle | String | 书名（瞬时字段） |
| userName | String | 用户名（瞬时字段） |
| borrowCode | String | 借阅单号（唯一） |
| borrowDate | LocalDateTime | 借阅日期 |
| dueDate | LocalDateTime | 应还日期 |
| returnDate | LocalDateTime | 实际归还日期 |
| status | Integer | 0=借阅中，1=已归还，2=已逾期，3=待审核续借 |
| renewCount | Integer | 续借次数 |
| overdueFine | Double | 逾期罚款 |
| operatorId | Long | 操作员ID |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |
| deleted | Integer | 逻辑删除 |

### 17.4 预约（Reservation）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| userId | Long | 用户ID |
| bookId | Long | 图书ID |
| bookTitle | String | 书名（瞬时字段） |
| userName | String | 用户名（瞬时字段） |
| reserveDate | LocalDateTime | 预约时间 |
| expireDate | LocalDateTime | 到期时间 |
| status | Integer | 0=等待中，1=可取书，2=已取消，3=已完成 |
| notified | Boolean | 是否已通知 |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |
| deleted | Integer | 逻辑删除 |

### 17.5 评论（BookComment）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| bookId | Long | 图书ID |
| userId | Long | 用户ID |
| rating | Integer | 评分 1-5 |
| content | String | 评论内容 |
| likeCount | Integer | 点赞数 |
| replyCount | Integer | 回复数 |
| parentId | Long | 父评论ID（回复） |
| createTime | LocalDateTime | 创建时间 |
| updateTime | LocalDateTime | 更新时间 |
| deleted | Integer | 逻辑删除 |

### 17.6 分类（Category）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| name | String | 分类名称 |
| parentId | Long | 父分类ID |
| sort | Integer | 排序 |
| bookCount | Integer | 图书数量（瞬时字段） |

### 17.7 公告（Notice）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| title | String | 标题 |
| summary | String | 摘要 |
| content | String | 内容（HTML） |
| publishDate | String | 发布日期 |
| isImportant | Boolean | 是否重要 |
| isActive | Boolean | 是否启用 |

### 17.8 数字资源（DigitalResource）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Long | 主键 |
| category | String | 分类：ebook/journal/media/database |
| name | String | 资源名称 |
| description | String | 描述 |
| url | String | 访问地址 |
| available | Boolean | 是否可用 |
| sortOrder | Integer | 排序 |

### 17.9 系统配置（SysConfig）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| configKey | String | 配置键 |
| configValue | String | 配置值 |

---

## 18. 错误码参考

### 18.1 HTTP状态码

| 状态码 | 含义 | 说明 |
|--------|------|------|
| 200 | 成功 | 请求正常处理 |
| 400 | 请求错误 | 参数校验失败、业务异常 |
| 401 | 未认证 | Token缺失、无效或过期 |
| 403 | 无权限 | 角色不匹配（非管理员访问管理接口） |
| 500 | 服务器错误 | 内部异常 |

### 18.2 业务异常

| code | message | 触发场景 |
|------|---------|----------|
| 400 | 用户名已存在 | 注册/新增用户 |
| 400 | 密码错误 | 登录 |
| 400 | 用户名或密码不能为空 | 登录 |
| 400 | 图书库存不足 | 借阅时库存为0 |
| 400 | 您已借阅过该图书 | 重复借阅 |
| 400 | 您已预约过该图书 | 重复预约 |
| 400 | 该评论不存在 | 点赞/取消点赞 |
| 400 | 您已点赞过该评论 | 重复点赞 |
| 401 | 未登录或登录已过期 | Token过期 |
| 403 | 权限不足 | 非管理员访问管理接口 |

---

> 文档维护：建议在接口变更时同步更新本文档。
> 后端源码：`library-management-backend/src/main/java/com/library/library/controller/`
> 前端API层：`library-management/src/api/`
