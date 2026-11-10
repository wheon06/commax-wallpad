# GitHub 배포

대상 저장소: `wheon06/commax-wallpad`, MIT 라이선스.

## 처음 공개

먼저 `pytest`, Ruff, `python tools/build.py`를 실행합니다. `commax_connection.json`, PCAP, HA 설정·로그가 커밋에 포함되지 않았는지 확인하세요. 공개 ZIP은 허용 목록으로 빌드되지만, 직접 git add를 할 때도 별도로 확인합니다.

GitHub CLI가 설치·인증된 환경에서 소스 폴더 안에서 실행할 수 있습니다.

```sh
gh auth status
git init -b main
git add .
git diff --cached --stat
git commit -m "Release COMMAX Wallpad integration"
gh repo create wheon06/commax-wallpad --public --source=. --remote=origin --push --description "COMMAX wallpad lights and exhaust fans for Home Assistant and Apple Home on the local network"
gh repo edit wheon06/commax-wallpad --add-topic home-assistant --add-topic hacs --add-topic commax --add-topic homekit
```

저장소가 이미 있다면 다시 만들지 말고 기존 remote와 내용을 확인한 뒤 push합니다. Actions의 테스트·hassfest·HACS 검증이 모두 완료된 것을 확인하고 태그를 만듭니다.

```sh
git tag v0.2.0
git push origin v0.2.0
```

릴리스 워크플로가 버전 일치와 테스트를 확인한 뒤 `commax_wallpad.zip`, 소스 ZIP, SHA256SUMS를 GitHub Release에 올립니다. GitHub 조직이나 계정 정책에 따라 Actions의 쓰기 권한 허용이 필요할 수 있습니다.

## 업데이트

1. `manifest.json` 버전과 CHANGELOG 변경.
2. 테스트·포맷 검사 후 main에 반영.
3. 같은 버전의 `vX.Y.Z` 태그 push.
4. Release ZIP과 HACS 사용자 지정 저장소 다운로드 확인.

HACS의 기본 목록에 자동 등재되는 것은 아닙니다. 사용자 지정 저장소로 먼저 배포하고 실제 다른 설치 환경의 호환성을 확인합니다.
