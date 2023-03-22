# 市值2.0

## http
### 统一路由
```
/app/v1
```
### 获取验证码

```json
// url参数
// GET  /login
{
  "username": ""
}
```

### 登陆

```json
// body-json参数
// POST  /login
{
  "username": "",
  "password": "",
  "verifyCode": ""
}
```

### 修改密码

```json
// body-json参数
// PUT  /login
{
  "password": ""  // 不传则重置密码
}
// cookie
{
  "token_id": ""
}
```

### 登出

```json
// DELETE  /login
// cookie
{
  "token_id": ""
}
```


## websocket

### 统一路由

```
/app/v1/ws
```

### REST请求

#### USER

##### admin

```json
// 获取用户信息
{
  "action": "rest",
  "channel": "user.admin",
  "method": "GET",
  "token_id": "",
  "username": none  // 此参数决定是否返回所有用户信息
}
```

```json
// 新增用户
{
  "action": "rest",
  "channel": "user.admin",
  "method": "POST",
  "token_id": "",
  "user_info": {
    "username": "",
    "password": "",
    "email": "",
    "team": "",
    "isManager": false
  },
  "user_perm": {
    "monCreate": false,
    "monDelete": false,
    "monUpdate": false,
    "monSearch": false,
    "monOrder": false,
    "monStrategy": false
  }
}
```

```json
// 修改用户信息
{
  "action": "rest",
  "channel": "user.admin",
  "method": "PUT",
  "token_id": "",
  "username": "",
  "initPwd": false,  // 是否重置密码
  "user_info": {
    "password": "",  // 非必传参数
    "email": "",
    "team": "",
    "isManager": false
  },
  "user_perm": {
    "monCreate": false,
    "monDelete": false,
    "monUpdate": false,
    "monSearch": false,
    "monOrder": false,
    "monStrategy": false
  }
}
```

```json
// 删除用户
{
  "action": "rest",
  "channel": "user.admin",
  "method": "DELETE",
  "token_id": "",
  "username": ""
}
```

##### operate

```json
// 获取操作记录
{
  "action": "rest",
  "channel": "user.operate",
  "method": "GET",
  "token_id": "",
  "username": "",
  "exchange": "lbk",
  "symbol": "",
  "startTime": "%Y-%m-%d %H:%M:%S",	 // 默认昨天
  "finalTime": "%Y-%m-%d %H:%M:%S",	 // 默认今天
  "page": 1,
  "per_page": 50
}
```

#### MARKET

##### coins

```json
// 获取所有币对数据
{
  "action": "rest",
  "channel": "market.coins",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk"
}
```

```json
// 新增币对
{
  "action": "rest",
  "channel": "market.coins",
  "method": "POST",
  "token_id": "",
  "exchange": "lbk",
  "new_coin": {
    "symbol": "",
    "f_coin": "",
    "f_coin_addr": "",
    "addr_type": "",
    "full_name": "",
    "account": "",
    "profit_rate": 0.5,
    "step_gap": 0.5,
    "order_amount": 10,
    "order_nums": 10,
    "if1m": false,
    "team": ""
  }
}
```

```json
// 修改币对
{
  "action": "rest",
  "channel": "market.coins",
  "method": "PUT",
  "token_id": "",
  "exchange": "lbk",
  "new_coin": {
    "symbol": "",
    "f_coin": "",
    "f_coin_addr": "",
    "full_name": "",
    "account": "",
    "profit_rate": 0.5,
    "step_gap": 0.5,
    "order_amount": 10,
    "order_nums": 10,
    "if1m": false,
    "team": ""
  }
}
```

```json
// 删除币对
{
  "action": "rest",
  "channel": "market.coins",
  "method": "DELETE",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

##### account

```json
// 获取账户
{
  "action": "rest",
  "channel": "market.account",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "account": none  //	此参数决定是否返回所有账户信息
}
```

```json
// 新增账户
{
  "action": "rest",
  "channel": "market.account",
  "method": "POST",
  "token_id": "",
  "exchange": "lbk",
  "new_account": {
    "account": "",
    "apiKey": "",
    "secretKey": "",
    "team": ""
  }
}
```

```json
// 修改账户
{
  "action": "rest",
  "channel": "market.account",
  "method": "PUT",
  "token_id": "",
  "exchange": "lbk",
  "new_account": {
    "account": "",
    "apiKey": "",
    "secretKey": "",
    "team": ""
  }
}
```

```json
// 删除账户
{
  "action": "rest",
  "channel": "market.account",
  "method": "DELETE",
  "token_id": "",
  "exchange": "lbk",
  "account": ""
}
```

##### report

```json
// 更新日报文件
{
  "action": "rest",
  "channel": "market.report",
  "method": "POST",
  "token_id": "",
  "new_file": ""  // byte类型
}
```

##### strategy

```json
// 查询策略状态
{
  "action": "rest",
  "channel": "market.strategy",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

```json
// 启动策略
{
  "action": "rest",
  "channel": "market.strategy",
  "method": "POST",
  "token_id": "",
  "exchange": "lbk",
  "symbol": "",
  "profit_rate": 0.5,
  "step_gap": 0.5,
  "order_amount": 10,
  "order_nums": 10,
}
```

```json
// 关闭策略
{
  "action": "rest",
  "channel": "market.strategy",
  "method": "DELETE",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

#### MONITOR

##### order

```json
// 查询挂单
{
  "action": "rest",
  "channel": "monitor.order",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": "",
  "page": 1,
  "per_page": 200
}
```

```json
// 下单（单个）
{
  "action": "rest",
  "channel": "monitor.order",
  "method": "POST",
  "token_id": "",
  "exchange": "lbk",
  "symbol": "",
  "type": "buy",
  "price": 0.5,
  "order_amount": 10.1
}
```

```json
// 下单（批量）
{
  "action": "rest",
  "channel": "monitor.order",
  "method": "POST",
  "token_id": "",
  "exchange": "lbk",
  "symbol": "",
  "batch": true,
  "type": "buy",
  "start_price": 0.5,
  "final_price": 0.9,
  "order_num": 10,
  "order_amount": 10.1,
  "random_index": 0.5
}
```

```json
// 撤单（单个or批量）
{
  "action": "rest",
  "channel": "monitor.order",
  "method": "DELETE",
  "token_id": "",
  "exchange": "lbk",
  "symbol": "",
  "order_ids": "id1,id2"  // 多个id用英文逗号分隔
}
```

```json
// 撤单（全部）
{
  "action": "rest",
  "channel": "monitor.order",
  "method": "DELETE",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

##### trade

```json
// 查询历史成交记录
{
  "action": "rest",
  "channel": "monitor.trade",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": "",
  "start_time": "1234567890",  // 时间戳（秒）
  "final_time": "1234567890",
  "limit": 100
}
```

##### balance

```json
// 查询账户余额
{
  "action": "rest",
  "channel": "monitor.balance",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

### subscribe订阅

#### MARKET

##### coins

```json
// 订阅所有币对数据, 5s
{
  "action": "subscribe",
  "channel": "market.coins",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk"
}
```

##### strategy

```json
// 订阅策略状态, 1s
{
  "action": "subscribe",
  "channel": "market.strategy",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

#### MONITOR

##### depth

```json
// 订阅深度信息, 0.5s
{
  "action": "subscribe",
  "channel": "monitor.depth",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

##### order

```json
// 订阅当前挂单, 2s
{
  "action": "subscribe",
  "channel": "monitor.order",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

##### trade

```json
// 订阅历史成交, 5s
{
  "action": "subscribe",
  "channel": "monitor.trade",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

##### balance

```json
// 订阅账户余额, 2s
{
  "action": "subscribe",
  "channel": "monitor.balance",
  "method": "GET",
  "token_id": "",
  "exchange": "lbk",
  "symbol": ""
}
```

### unsubscribe取消订阅

```json
// 取消订阅所有币对数据
{
  "action": "unsubscribe",
  "channel": "market.coins",
  "token_id": ""
}

// 取消订阅策略状态
{
  "action": "unsubscribe",
  "channel": "market.strategy",
  "token_id": ""
}

// 取消订阅深度信息
{
  "action": "unsubscribe",
  "channel": "monitor.depth",
  "token_id": ""
}

// 取消订阅当前挂单
{
  "action": "unsubscribe",
  "channel": "monitor.order",
  "token_id": ""
}

// 取消订阅历史成交
{
  "action": "unsubscribe",
  "channel": "monitor.trade",
  "token_id": ""
}

// 取消订阅账户余额
{
  "action": "unsubscribe",
  "channel": "monitor.balance",
  "token_id": ""
}
```
