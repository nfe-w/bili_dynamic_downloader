# bili_dynamic_downloader
【B站】UP主动态爬取、动态图片下载

- 下载 https://space.bilibili.com/672328094/dynamic 的动态保存为json（以嘉然为例🥰）
- 支持动态图片保存（以动态时间进行文件夹分组，并将动态的文字进行保存）
- 使用协程提高下载速度

## 使用方法

```shell
pip install -r requirements.txt
# 修改 bili_dynamic_downloader.py 中的 uid
python3 bili_dynamic_downloader.py
```

> 参考 https://github.com/Starrah/BilibiliGetDynamics ，并加以修改，感谢
