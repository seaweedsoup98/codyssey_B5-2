# B5-2 | Mini Git

Git의 핵심 개념을 **커밋 메타데이터**로 구현한 Python CLI 프로그램입니다. 브랜치, 커밋 그래프(DAG), 그래프 탐색, 정렬, 역색인을 직접 다룹니다. 파일 내용은 추적하지 않으며 실제 Git을 대체하지 않습니다.

## 실행

- Python **3.10 이상**, 외부 패키지 불필요
- 저장소 루트에서 실행:

```bash
python main.py
```

`mini-git>` 프롬프트에 명령을 입력합니다. `exit`, `quit` 또는 EOF(Ctrl+D / Windows의 Ctrl+Z, Enter)로 종료합니다. 데이터는 메모리에만 저장되므로 종료하면 사라집니다.

## 명령어

| 명령어 | 기능 |
| --- | --- |
| `INIT <user_name>` | 저장소 초기화, `main` 및 작성자 설정 |
| `BRANCH <branch_name>` | 현재 브랜치의 끝을 가리키는 새 브랜치 생성 |
| `SWITCH <branch_name>` | 현재 브랜치 전환 |
| `COMMIT <message>` | 커밋 생성, 부모 연결, 인덱스 갱신 |
| `LOG` | **부모가 자식보다 먼저** 나오는 커밋 로그 |
| `LOG --sort-by=date` | 커밋 시각 기준 오름차순 정렬 |
| `LOG --sort-by=author` | 작성자 이름 기준 오름차순 정렬 |
| `PATH <hash1> <hash2>` | 부모 연결을 무방향으로 보았을 때 최단 경로 |
| `ANCESTORS <hash>` | 해당 커밋의 모든 조상 |
| `SEARCH <keyword>` | 커밋 메시지 역색인 검색 |
| `SEARCH --author=<name>` | 작성자 역색인 검색 |
| `exit` / `quit` | 종료 |

- 명령어와 옵션 이름은 대소문자를 구분하지 않습니다.
- 공백을 포함하는 **사용자명, 메시지, 검색어, 작성자명**은 따옴표로 묶습니다.
- 키워드는 공백으로 나눈 단어를 소문자로 일치시킵니다. 따옴표로 묶은 여러 단어는 단어별 후보를 찾은 뒤 연속된 구절인지 확인합니다.
- 브랜치 이름과 작성자 이름의 **값**은 입력한 대소문자를 유지합니다. 작성자 검색은 정확히 같은 이름을 찾습니다.
- `INIT`를 다시 실행하면 커밋, 브랜치, 인덱스가 초기화됩니다. 커밋 식별자 번호는 현재 실행 중 중복되지 않도록 계속 증가합니다.

## 실행 예시

```text
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice
mini-git> commit "Initial commit"
[main 00000001] Initial commit
mini-git> branch feature
Created branch: feature
mini-git> switch feature
Switched to branch: feature
mini-git> commit "Add login feature"
[feature 00000002] Add login feature
mini-git> switch main
Switched to branch: main
mini-git> commit "Add payment feature"
[main 00000003] Add payment feature
mini-git> path 00000002 00000003
Path: 00000002 -> 00000001 -> 00000003
mini-git> search LOGIN
Found 1 commit(s):
commit 00000002 (Alice, <UTC timestamp>)
  Add login feature
mini-git> quit
```

실제 출력에서 `<UTC timestamp>` 위치에는 커밋 생성 시점의 ISO 8601 시각이 출력됩니다. hash는 **실제 Git SHA가 아닌 중복 없는 증가형 식별자**입니다.

## 파일 구성

```text
main.py              커밋 자료구조, 그래프·정렬·검색 알고리즘, CLI
README.md            실행 방법과 명령어
.gitignore           Python 임시 파일 제외
tests/test_main.py   자동 테스트와 실제 REPL 실행 검증
docs/LEARNING.md     처음부터 읽는 구현 해설과 핵심 개념
docs/EVALUATION.md   예상 질문과 답변 요점 및 코드 위치
```

## 검증

저장소 루트에서 다음을 실행합니다.

```bash
python -m unittest discover -s tests -v
```

저장소 초기화·재초기화, 커밋 식별자, 브랜치 분기, DAG 로그, 최단 경로 및 사전순 동률, 조상 탐색, 역색인, 안정 병합 정렬, 입력 오류, 실제 REPL 동작을 확인합니다.

## 학습 순서

1. `main.py`의 `main()` → `MiniGit.execute()`를 읽고 입출력 흐름을 파악합니다.
2. [LEARNING.md](docs/LEARNING.md)를 읽으며 상태 → 커밋 그래프 → 탐색 → 역색인 → 정렬 순서로 코드를 확인합니다.
3. `tests/test_main.py`에서 실제 입력과 기대 결과를 연결합니다.
4. [EVALUATION.md](docs/EVALUATION.md)를 보고 코드를 근거로 핵심 내용을 설명해 봅니다.

**구현 범위:** 필수 명령만 포함합니다. 선택 과제인 `DIFF`, `MERGE`, 정렬 알고리즘 성능 비교는 제외했습니다. 그래프 전용 라이브러리와 `sorted()`, `list.sort()` 등 표준 정렬 API는 사용하지 않습니다.
