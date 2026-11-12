# FINAL FANTASY VII EVER CRISIS 한글패치

스토리 대사, 시스템 UI, 무비 자막을 한국어로 바꿔 주는 **비공식 팬 패치**입니다.
공식 서비스가 끝난 뒤 팬 오프라인 서버 **[NeverCrisis](https://github.com/ShadowMPo/NeverCrisis)** 환경에서 플레이하는 것을 전제로 만들었습니다.

## 준비물
- Steam으로 설치한 FINAL FANTASY VII EVER CRISIS
  (기본 위치: `C:\Program Files (x86)\Steam\steamapps\common\FF7EC`)
- 게임 폴더에 오프라인 서버 **[NeverCrisis](https://github.com/ShadowMPo/NeverCrisis)**(`FF7ECServer.exe`, `FF7ECServer.pak`)가 이미 설치되어 있고,
  **한글패치 없이도 게임이 실행되는 상태**. 오프라인 서버는 이 패치에 들어 있지 않으니 따로 받아야 합니다.
- Windows 10/11 64비트, .NET Framework 4.8 (Windows 10/11에 기본 포함)
- 첫 실행 때만 인터넷 연결 (BepInEx가 Unity 기본 라이브러리를 내려받습니다)

> 설치 전에 게임 폴더(특히 세이브)를 백업해 두기를 권장합니다.

## 오프라인 서버 설치 (NeverCrisis)
한글패치보다 먼저 서버를 설치하세요. 자세한 내용은 [NeverCrisis 저장소](https://github.com/ShadowMPo/NeverCrisis)의 안내를 따르세요.
1. [NeverCrisis Releases](https://github.com/ShadowMPo/NeverCrisis/releases/latest)에서 서버 패키지를 내려받습니다.
2. 게임 폴더에 그대로 풉니다.
3. `FF7ECServer.exe`를 실행해 **한글패치 없이** 게임이 정상적으로 실행되는지 먼저 확인합니다.
   - 실행할 때마다 hosts 파일을 고치느라 관리자 권한을 요청합니다.
   - 443 포트가 비어 있어야 합니다.
   - `octo` 폴더에 없는 게임 파일은 Square Enix 일본 파일 서버에서 내려받습니다.
4. 정상 실행을 확인했으면 게임을 끄고 아래 한글패치 설치로 넘어갑니다.
   한글패치를 설치한 뒤에는 `FF7ECServer.exe` 대신 `FF7EC_KO.exe`로 실행합니다. `FF7EC_KO.exe`가 서버를 대신 띄워 줍니다.

서버 자체의 문제(접속, 세이브, 아이템 등)는 한글패치가 아니라 NeverCrisis 쪽 [Issues](https://github.com/ShadowMPo/NeverCrisis/issues)에 문의하세요.

## 설치
1. [Releases](../../releases/latest)에서 `FF7EC_KO_v1.0.zip`을 내려받습니다.
2. 게임 폴더를 엽니다. Steam 라이브러리에서 게임을 오른쪽 클릭 → **관리 → 로컬 파일 보기**를 누르면 됩니다.
3. zip 안의 내용을 **게임 폴더에 그대로** 풉니다. `FF7EC.exe`, `FF7ECServer.exe`와 같은 위치에 `FF7EC_KO.exe`가 있어야 합니다.
   같은 이름의 파일이 있다고 나오면 덮어씁니다.

   ```
   FF7EC   ├─ FF7EC.exe              (원래 있던 게임)
   ├─ FF7ECServer.exe        (원래 있던 오프라인 서버)
   ├─ FF7EC_KO.exe           ← 한글패치 실행기
   ├─ winhttp.dll, doorstop_config.ini, dotnet\   ← BepInEx 로더
   ├─ BepInEx\               ← 플러그인과 번역 파일
   ├─ ko_patch\              ← 폰트 패치기와 Pretendard 폰트
   ├─ uninstall_ko.bat       ← 제거 스크립트
   └─ 한글패치_설명.txt
   ```
   zip을 풀었을 때 `FF7EC_KO_v1.0\` 같은 폴더가 하나 더 생겼다면 그 **안의 내용물**을 게임 폴더로 옮기세요.

## 첫 실행
1. 게임 폴더의 `FF7EC_KO.exe`를 실행합니다. 서버가 hosts 파일을 고쳐야 해서 **관리자 권한 요청**이 뜹니다. "예"를 누르세요.
2. 첫 실행은 오래 걸립니다. **창이 안 보여도 끄지 말고 기다리세요.**
   - 한글 폰트 적용(30초쯤): 게임 폰트 파일 3개를 바꿉니다. 메뉴·대사는 Pretendard, 전투 화면은 Windows의 맑은 고딕을 씁니다. 원본은 `ko_patchackup`에 보관됩니다.
   - BepInEx 초기화(5~10분): 게임 코드를 분석하고 라이브러리를 내려받습니다. 두 번째부터는 빠릅니다.
3. 타이틀 화면과 메뉴가 한국어로 나오면 설치가 끝난 것입니다.

## 평소 실행
- **항상 `FF7EC_KO.exe`로 실행하세요.** Steam의 "플레이" 버튼이나 `FF7EC.exe`로 실행하면 서버가 뜨지 않습니다.
- 실행기가 하는 일은 다음과 같습니다.
  1. 오프라인 서버를 창 없이 띄웁니다.
  2. 폰트가 원래대로 돌아가 있으면 다시 적용합니다.
  3. 게임을 실행합니다.
  4. 게임을 닫으면 서버를 정상 종료해서 hosts 파일을 원래대로 돌려 놓습니다.
- 바로가기를 바탕화면에 만들어 두면 편합니다(`FF7EC_KO.exe` 오른쪽 클릭 → 보내기 → 바탕 화면).
- 실행기에 준 명령줄 인자는 그대로 `FF7ECServer.exe`에 넘어갑니다. 서버 옵션을 쓰려면 바로가기의 "대상" 뒤에 붙이세요.

## 게임 업데이트·무결성 검사 후
- Steam의 "게임 파일 무결성 검사"로 폰트 파일이 원래대로 돌아가도, 다음에 `FF7EC_KO.exe`로 실행하면 자동으로 다시 적용됩니다.
- 무결성 검사는 BepInEx나 번역 파일을 지우지 않습니다. 혹시 한국어가 전혀 안 나오면 zip을 다시 풀어 덮어쓰세요.

## 제거
1. 게임을 완전히 끕니다.
2. 게임 폴더의 `uninstall_ko.bat`를 오른쪽 클릭 → **관리자 권한으로 실행**합니다.
3. 폰트 원본을 되돌리고, 이 패치로 설치한 파일(BepInEx 포함)을 지웁니다. 오프라인 서버와 세이브는 건드리지 않습니다.

## 문제 해결
| 증상 | 해결 |
|---|---|
| "FF7ECServer.exe를 찾을 수 없습니다" | `FF7EC_KO.exe`가 게임 폴더(서버와 같은 위치)에 있는지 확인하세요. 폴더째 풀린 경우 내용물을 꺼내세요. |
| "이미 실행 중입니다" | 이전에 띄운 게임이나 서버가 남아 있습니다. 작업 관리자에서 `FF7EC`, `FF7ECServer`를 끝낸 뒤 다시 실행하세요. |
| 첫 실행 때 아무 창도 안 뜸 | BepInEx 초기화 중입니다. 10분쯤 기다리세요. `BepInEx\LogOutput.log`가 계속 커지고 있으면 정상입니다. |
| 한국어가 전혀 안 나옴 | `BepInEx\LogOutput.log`가 있는지 보세요. 없으면 `winhttp.dll`이 게임 폴더에 있는지, 백신이 지우지 않았는지 확인하세요. |
| 글자가 네모(□)로 나옴 | 폰트 적용이 실패한 것입니다. `ko_patchontpatch.log`를 확인하고 `FF7EC_KO.exe`를 관리자 권한으로 다시 실행하세요. |
| "hosts 파일이 원복되지 않았을 수 있습니다" | 서버가 강제 종료된 경우입니다. `C:\Windows\System32\drivers\etc\hosts`에 서버가 추가한 줄이 남아 있는지 확인하세요. 다음 실행 때 서버가 다시 정리합니다. |
| 일부 문장이 일본어·영어로 나옴 | 아직 번역이 없는 문장입니다. 아래 "제보"로 알려 주세요. |

실행 기록은 게임 폴더의 `ff7ec_ko_launcher.log`, `ff7ec_ko_server.log`, `ko_patchontpatch.log`, `BepInEx\LogOutput.log`에 남습니다. 문제를 제보할 때 함께 첨부해 주세요.

## 번역에 대해
- 일본어 원문을 기준으로 AI(DeepSeek) 초벌 번역 후 검수했습니다. 고유명사와 용어는 FINAL FANTASY VII REBIRTH 한국어판 표기를 따랐습니다.
- 18,000줄이 넘는 분량이라 오역이나 어색한 문장이 남아 있을 수 있습니다.
- 오역, 미번역, 깨진 화면은 [Issues](../../issues)에 스크린샷과 함께 올려 주세요.

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
- 오프라인 서버: [NeverCrisis](https://github.com/ShadowMPo/NeverCrisis) (별도 배포, 이 패치에 포함되지 않음)
- 번역 초벌: [GalTransl](https://github.com/xd2333/GalTransl) + DeepSeek, 검수와 다듬기는 사람과 AI가 함께 했습니다.

## 주의
FINAL FANTASY VII EVER CRISIS와 관련 상표·저작물의 권리는 SQUARE ENIX에 있습니다.
이 프로젝트는 SQUARE ENIX, Applibot과 관계없는 팬 제작물입니다. 무료로 배포하며 판매를 금지합니다.
사용에 따른 문제(세이브 손상, 설치 손상 등)는 책임지지 않습니다.
