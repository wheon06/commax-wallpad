# 본인의 연결 정보 확인

모델명으로 서버 주소·인증정보를 자동 결정하지 않습니다. 본인 세대의 공식 앱이 사용하는 통신을 확인하세요.

확인할 항목:

- TCP 연결 목적지 → HTTP 프록시 주소와 포트.
- `POST http://... HTTP/1.1` 요청 줄 → 월패드 SOAP 주소.
- `Proxy-Authorization: Basic ...` → 프록시 사용자 이름과 비밀번호.
- SOAP `getLightItem` / `setLight` → 지원하는 전등 채널 통신인지 확인.

iPhone + Mac에서는 Apple의 RVI 패킷 수집을 사용할 수 있습니다. USB로 연결해 신뢰를 허용하고 UDID로 RVI를 생성한 뒤, 공식 앱에서 전등 하나를 켜고 끌 때의 통신을 수집합니다. HTTP 프록시 앱에서 아무것도 보이지 않더라도 앱 자체가 다른 HTTP 프록시로 직접 통신할 수 있습니다.

```sh
rvictl -s YOUR_IPHONE_UDID
sudo tcpdump -i rvi0 -nn -s 0 -w /tmp/commax.pcap 'tcp'
```

짧게 수집하고 Control+C로 종료합니다. Mac에서 로컬 추출:

```sh
python3 tools/capture.py /tmp/commax.pcap --output commax_connection.json
```

도구는 요청을 보내지 않고 인증값도 출력하지 않습니다. 생성 파일은 권한 600으로 저장합니다. 두 개 이상의 연결이 나오면 `--connection 0` 같은 명시적 번호로 선택하세요. 원본 캡처는 저장소에 추가하지 마세요.

읽기 전용 확인:

```sh
python3 tools/check.py --config commax_connection.json --order YOUR_CHANNEL_NUMBER
```

PCAP·PCAPNG, IPv4 TCP, Ethernet·loopback·raw IP·Apple PKTAP 캡처를 지원합니다. 연결된 TCP 조각은 재조립하지만 누락 조각을 추측하지 않습니다. IPv6, TLS 암호화, IP 단편 재조립 등은 미지원입니다. 캡처에는 로그인·동호수·토큰이 포함될 수 있어 원본을 공개 이슈에 첨부하지 않습니다.

참고: [Apple RVI 수집 안내](https://developer.apple.com/documentation/network/recording-a-packet-trace)
