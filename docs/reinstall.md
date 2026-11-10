# 업그레이드와 깔끔한 재설치

## 기존 이름을 유지하는 업그레이드

Home Assistant 백업을 먼저 만듭니다. 새 소스를 다른 폴더에 압축 해제하고 HA 컨테이너를 멈춘 뒤 실행합니다.

```sh
python3 tools/install.py --config-dir /YOUR/EXISTING/HA/CONFIG
```

기존 연동 코드는 `commax_backups/`에 tar.gz로 백업됩니다. 연결 JSON·HA 계정·엔티티 레지스트리는 수정하지 않습니다. HA를 다시 시작하면 버전 1 설정을 버전 2로 이전하고 기존 `unique_id`를 유지합니다. 유형이 바뀌지 않은 채널은 기존 엔티티 ID와 이름을 유지합니다.

예전 `tools/check.py`를 계속 쓰려면 새 CLI에서는 채널과 파일 위치를 명시합니다.

```sh
python3 tools/check.py --config /YOUR/HA/CONFIG/commax_connection.json --order YOUR_CHANNEL
```

## COMMAX WAN Test 정리

이 도구는 대화 중 만들었던 **이름 `COMMAX WAN Test` + 포트 `21065`**의 YAML 브리지에만 적용됩니다. 다른 이름·다른 포트·`!include` 구조는 자동 정리하지 않습니다.

```sh
python3 tools/cleanup_test_bridge.py --config-dir /YOUR/HA/CONFIG
```

미리보기에서 대상이 맞으면 다음을 실행합니다. 쓰기 권한이 없으면 이 명령에만 sudo를 붙이세요.

```sh
python3 tools/cleanup_test_bridge.py --config-dir /YOUR/HA/CONFIG --apply
```

`configuration.yaml` 백업이 `commax_backups/`에 만들어집니다. HA를 재시작하고, **HA의 HomeKit Bridge 통합에서 COMMAX WAN Test 항목도 삭제**하세요. YAML만 없애도 가져온 설정 항목이 남을 수 있습니다. 아이폰 홈 앱에서도 홈 설정 → 홈 허브 및 브리지에서 시험용 브리지만 제거합니다.

공유기의 TCP 21065 포트포워딩과 시험용 UFW 규칙을 추가했다면 해당 규칙만 제거합니다.

```sh
sudo ufw delete allow proto tcp from 0.0.0.0/0 to any port 21065
```

기존 내부망용 21064 등은 실제 사용 중이면 유지합니다. 네트워크·방화벽 전체를 초기화하지 않습니다.

## 이번 코맥스 액세서리만 새로 등록하고 싶다면

이 절차는 선택한 브리지의 Apple 홈 방·장면·자동화 연결을 잃을 수 있습니다. 필요한 이름·방 배정을 먼저 기록하세요. HomeKit Bridge에 다른 제조사 기기가 함께 있다면 그 브리지를 통째로 삭제하지 말고 코맥스 항목만 제외하거나 별도 브리지로 분리하세요.

1. 아이폰 홈 앱에서 시험용 브리지와 **코맥스 전용 기존 브리지**를 제거합니다. 집 전체를 삭제하지 않습니다.
2. HA → 설정 → 기기 및 서비스 → HomeKit Bridge에서 같은 브리지 항목을 삭제합니다.
3. HA의 COMMAX Wallpad 설정 항목을 삭제합니다. 기존 `commax_connection.json`은 보관합니다.
4. 위 설치 도구로 새 연동을 설치하고 HA를 재시작합니다.
5. COMMAX Wallpad 추가 → 기존 파일 가져오기 또는 직접 입력.
6. 실제 전등·배기 번호를 분류하고 이름을 정합니다.
7. HomeKit Bridge를 **하나만** 만들고 코맥스 엔티티를 선택합니다.
8. 같은 LAN의 아이폰에서 새 QR을 스캔합니다.

새 배포에는 시험용 WAN 브리지와 고정된 집별 번호가 들어 있지 않습니다. 기존 설치의 `.storage`, 연결 파일, HomeKit 상태 파일을 수동으로 통째로 지우지 마세요.
