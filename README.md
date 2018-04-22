# txffp_tools
票根网(pss.txffp.com)的发票批量下载或者批量开票工具

### 简介
该脚本只适用于该站点[https://pss.txffp.com/](https://pss.txffp.com/)，可以帮助网友进行发票文件的批量下载和批量开票。</br>


### 使用方式
```shell
# 安装requests和lxml
$ python3 -m pip install -r requirements.txt 

# 使用浏览器登陆成功后，拷贝cookie信息至当前目录下的cookie.txt文件内并保存
# 开始运行脚本
$ python3 run.py --help
```

### 参数简介
```
optional arguments:
  -h, --help            show this help message and exit
  -d, --download        下载发票文件，需要指定对象，以及月份和保存目录
  -i, --invoicev        开票，需要指定开票月和对象
  -a, --all             执行全部
  -c CARDID, --cardid CARDID
                        指定车辆编号，注意：cardid不是指车牌号（不推荐）
  -e EMAIL, --email EMAIL
                        开票时的发票文件接收邮箱地址
  -m MONTH, --month MONTH
                        目标年月份，例如2018年4月为：201804
  -s SAVEDIR, --savedir SAVEDIR
                        发票文件保存路径
  -w, --waite           是否在每次进行网络请求间进行睡眠(默认睡眠1-3秒)，可减轻对方服务器鸭梨
  ```
  
  ### 使用范例
  ```shell
  # 下载2018年4月份的全部发票
  $ python3 run.py -d -m 201804 -a -s 发票保存路径
  
  # 对2018年4月份的车牌号全部执行开票
  $ python3 run.py -i -m 201804 -a -e example@email.com
  ```
  
  ### 提示
  * 如果执行中因为网络原因下载出错，只能重新进行下载
  * 默认只会执行5页的内容，如果超过5页，需要自己修改代码
  * 不保证该工具持续有效，我也不会进行持续维护
