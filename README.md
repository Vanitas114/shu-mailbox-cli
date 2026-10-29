# shu-mailbox-cli 使用说明

这个小程序尝试使用企业微信扫码登录上海大学邮箱，并查询收件箱、待办邮件、草稿箱和已发送。列表显示联系人、主题和日期，不显示邮件正文。扫码登录和真实邮箱查询仍需要实际验证。

## 依赖与致谢

本项目的统一身份认证与企业微信扫码登录流程依赖 [shu-sso-poc](https://github.com/preca-hoshino/shu-sso-poc)，相关代码已包含在项目中。感谢原作者 [preca-hoshino](https://github.com/preca-hoshino) 的工作与分享！

## 第一次使用

1. 确认电脑已安装 Python 3.10 或更新版本，并且可以访问上海大学邮箱和企业微信。

2. 安装运行所需的组件：

   ```powershell
   python -m pip install -r requirements.txt
   ```

## 开始使用

在shu-mailbox-cli目录下面运行：

```powershell
python shu_mailbox_cli.py
```

程序显示二维码后，打开手机企业微信，使用“扫一扫”扫描，并在手机上确认登录。等待终端显示结果。登录成功后，输入数字选择文件夹：

- `1`：收件箱
- `2`：待办邮件
- `3`：草稿箱
- `4`：已发送
- `q`：退出

查看列表时输入 `n` 查看下一页，`p` 查看上一页，`r` 刷新，`b` 返回文件夹选择，`q` 退出。每次输入后按回车。

## 遇到问题

- 如果二维码过期或扫码未完成，重新运行 `python shu_mailbox_cli.py` 获取新二维码。
- 如果二维码显示不完整，请拉宽终端窗口后重新运行；颜色显示异常时，可以尝试 `python shu_mailbox_cli.py --qr-style ascii`。
- 按 `Ctrl+C` 可以结束程序。
- 如果出现其他错误，请记录终端中的错误提示，方便排查。二维码和登录信息请勿分享给他人。
