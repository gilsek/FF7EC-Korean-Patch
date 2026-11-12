# FINAL FANTASY VII EVER CRISIS 한글패치

스토리 대사, 시스템 UI, 무비 자막을 한국어로 바꿔 주는 **비공식 팬 패치**입니다.
공식 서비스가 끝난 뒤 오프라인 서버(NeverCrisis) 환경에서 플레이하는 것을 전제로 만들었습니다.

## 설치
[Releases](../../releases)에서 `FF7EC_KO_v1.0.zip`을 받아 게임 폴더(`FF7EC.exe`가 있는 곳)에 풀고 `FF7EC_KO.exe`로 실행하세요.
자세한 설치·제거 방법은 압축 파일 안의 `한글패치_설명.txt`를 보세요.

## 구성
| 폴더 | 내용 |
|---|---|
| `plugin/StoryKo` | 스토리 대사를 ID 기준으로 한국어로 바꾸는 BepInEx 플러그인 |
| `plugin/TypewriterFix` | 한글 타자기 효과 보정 플러그인 |
| `patcher/FontPatch` | 게임 폰트 에셋에 한글 폰트를 넣는 패처 (AssetsTools.NET) |
| `launcher` | 서버 실행·폰트 적용·게임 실행을 묶은 런처 `FF7EC_KO.exe` |
| `translations` | XUnity.AutoTranslator용 추가 번역 파일 |
| `tools` | 번역 추출·점검·배포 빌드 스크립트 |
| `dist_files` | 배포판에 들어가는 설명서, 제거 스크립트, 라이선스 |

이 저장소에는 게임 원본 데이터(추출한 원문 텍스트, 에셋)와 게임 데이터 복호화 키가 **들어 있지 않습니다**.
그래서 `tools`의 일부 추출 스크립트(`ff7crypt`, `octo` 모듈을 쓰는 것)는 그대로는 돌아가지 않습니다.
번역 결과물은 Releases의 배포판에 들어 있습니다.

## 사용한 것
- [BepInEx](https://github.com/BepInEx/BepInEx) (LGPL-2.1)
- [XUnity.AutoTranslator](https://github.com/bbepis/XUnity.AutoTranslator) (MIT)
- [AssetsTools.NET](https://github.com/nesrak1/AssetsTools.NET) (MIT)
- [Pretendard](https://github.com/orioncactus/pretendard) (SIL OFL 1.1)
- 번역 초벌: [GalTransl](https://github.com/xd2333/GalTransl) + DeepSeek, 검수와 다듬기는 사람과 AI가 함께 했습니다.

## 주의
FINAL FANTASY VII EVER CRISIS와 관련 상표·저작물의 권리는 SQUARE ENIX에 있습니다.
이 프로젝트는 SQUARE ENIX와 관계없는 팬 제작물이며, 사용에 따른 책임은 사용자에게 있습니다.
