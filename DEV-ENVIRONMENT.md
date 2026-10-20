# DEV-ENVIRONMENT

확인일: 2026-10-19. 아래 값은 이 날짜에 명령을 실행해 얻은 결과다.

## 운영체제 · 셸

| 항목 | 값 |
|---|---|
| 운영체제 | Microsoft Windows 11 Pro 10.0.22631 |
| 셸 | PowerShell 7.6.7 (주 사용). Git Bash 도 쓸 수 있다. |

## 도구별 버전

`--version` 실행 결과를 그대로 적었다.

| 도구 | 명령 | 결과 |
|---|---|---|
| git | `git --version` | `git version 2.56.0.windows.2` |
| node | `node --version` | `v24.22.0` |
| npm | `npm --version` | `11.19.1` |
| uv | `uv --version` | `uv 0.13.1 (62faed335 2026-10-13 x86_64-pc-windows-msvc)` |
| python | `python --version` | `Python` (종료 코드 9009) |
| python (uv 관리) | `python3.12 --version` | `Python 3.12.15` |

### python 에 대한 설명

`python` 명령은 Windows 스토어 연결 파일(`C:\Users\EZ\AppData\Local\Microsoft\WindowsApps\python.exe`)이라 버전이 나오지 않는다. 쓸 수 있는 Python 은 uv 가 설치한 3.12.15 이다. Python 작업은 `uv` 로 한다.

## 새로 설치한 것

위 도구(git, node, npm, uv, uv 관리 Python)는 모두 이미 설치되어 있었다. 아래는 M0 에서 프로젝트 안에 설치한 패키지다. 버전은 2026-10-19 설치 직후 `uv pip list` 와 `npm ls --depth=0` 으로 확인했다.

### backend (uv, Python 3.12.15)

| 패키지 | 버전 | 설치 명령 |
|---|---|---|
| fastapi | 0.146.0 | `uv add "fastapi[standard]"` |
| uvicorn | 0.54.0 | 위 명령에 포함 |
| starlette | 1.9.0 | 위 명령에 포함 |
| pydantic | 2.14.1 | 위 명령에 포함 |
| python-multipart | 0.0.32 | 위 명령에 포함 |
| pytest | 9.1.1 | `uv add --dev pytest` |

`fastapi[standard]` 가 함께 설치한 나머지 패키지는 `backend/uv.lock` 에 있다.

### frontend (npm)

생성 명령: `npm create vite@latest frontend -- --template react-ts` (create-vite 9.3.0), 이어서 `npm install`.

| 패키지 | 버전 |
|---|---|
| react | 19.3.1 |
| react-dom | 19.3.1 |
| vite | 8.3.4 |
| @vitejs/plugin-react | 6.1.2 |
| typescript | 7.0.2 |
| oxlint | 1.88.0 |
| @types/node | 24.19.2 |
| @types/react | 19.3.0 |
| @types/react-dom | 19.3.0 |

### 설치하지 않은 것

Vercel CLI 는 M0 범위가 아니라 설치하지 않았다.

SQLite 는 파이썬 표준 라이브러리(`sqlite3`)라 따로 설치하지 않는다 (D-019).
