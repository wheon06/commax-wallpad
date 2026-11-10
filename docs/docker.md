# Ubuntu + Docker

기존 Home Assistant가 있다면 새 인스턴스를 띄우지 말고 실제 `/config` 볼륨에 커스텀 연동만 설치하세요.

새 설치는 저장소 폴더에서 다음을 실행합니다.

```sh
mkdir -p homeassistant
cp examples/compose.yaml compose.yaml
python3 tools/install.py --config-dir ./homeassistant
docker compose up -d
```

`http://서버의내부IP:8123`에서 계정을 만들고 COMMAX Wallpad를 추가합니다. 연결 정보는 본인의 값으로 입력하세요. 캡처에서 만든 파일이 있다면 `homeassistant/commax_connection.json`에 복사하고 기존 파일 가져오기를 선택할 수 있습니다. 권한은 `chmod 600`으로 제한합니다.

내부망이 192.168.0.0/24이고 실제 HomeKit 포트가 21064인 예:

```sh
sudo ufw allow from 192.168.0.0/24 to any port 8123 proto tcp
sudo ufw allow from 192.168.0.0/24 to any port 21064 proto tcp
sudo ufw allow from 192.168.0.0/24 to any port 5353 proto udp
```

실제 내부망과 브리지 포트에 맞춰 변경하세요. 예제는 Bluetooth를 사용하지 않으며 D-Bus나 추가 네트워크 관리 권한을 부여하지 않습니다. HomeKit은 `network_mode: host`로 로컬 검색을 사용합니다.

코드 업그레이드:

```sh
docker compose stop homeassistant
python3 tools/install.py --config-dir ./homeassistant
docker compose up -d
```

설치 도구가 설정 폴더에 쓸 수 없다면 폴더 소유권을 확인하세요. 필요한 경우 설치 명령만 `sudo python3 ...`로 실행할 수 있습니다. 전체 HA 설정 폴더를 누구나 쓸 수 있게 권한을 풀 필요는 없습니다.
