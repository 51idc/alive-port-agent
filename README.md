## Usage

```bash
mv cfg.example.json cfg.json
pip install -r requirement.txt
./contorl start
```

## Config
```
{
  "step": 60,
  "timeout": 5,     #单个端口执行nc的超时时间
  "debug": true,
  "transfers": [
    "192.168.6.222:6060"
  ],
  "http": 2223,
  "DC": "HL",
  "targets": {
    "alive-port-test": {
      "ip": "192.168.6.222",
      "ports": "5678;2222;80;8080"
    },
    "alive-port-test2": {
      "ip": "192.168.6.9",
      "ports": "5678;2222;80;8080"
    }
  }
}
```

## Metrics
```
{
    "alive.port.alive":"采集器状态（1存活，0不存活）",
    "alive.port.port_alive":"端口存活状态（1存活，0不存活）"
}
```
