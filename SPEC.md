# Claude Code Session Manager (CCSM) 設計規格

## 1. 概述

**工具名稱**: Claude Code Session Manager (CCSM)
**目標**: 提供 CLI 和 TUI 介面，用於管理 Claude Code 的專案和會話資料
**排除範圍**: 不包含 OMC (oh-my-claudecode) 相關功能

---

## 2. 數據存儲結構分析

### 2.1 全域數據 (~/.claude/)

#### 直接關聯 (以 session_id 直接標識)

| 目錄/檔案 | 說明 | 刪除策略 |
|-----------|------|----------|
| `tasks/{session_id}/` | 工作任務列表 (1.json, 2.json...) | 直接刪除整個目錄 |
| `todos/*{session_id}*` | 待辦事項 JSON (glob pattern) | 匹配刪除 |
| `plans/*.md` | 已儲存的 plans（Markdown） | 僅當只有一個 session 引用時刪除 |
| `sessions/*.json` | Session marker files（依 JSON 內容中的 sessionId） | 讀取 JSON 內容匹配後刪除 |
| `teams/{session_id}/` | Team data directory | 直接刪除整個目錄 |
| `session-env/{session_id}/` | Session 環境變數 | 直接刪除目錄 |
| `history.jsonl` | 對話歷史，每行含 sessionId | 流式重寫移除特定 session |
| `debug/{session_id}.txt` | 調試日誌 | 直接刪除 |
| `telemetry/1p_failed_events.{session_id}.{event_id}.json` | 遙測失敗事件，檔名含 session_id | 匹配檔名中的 session ID 刪除 |
| `file-history/{session_id}/` | 檔案編輯歷史快照 | 直接刪除目錄 |

#### 間接關聯 (需追蹤引用)

| 目錄/檔案 | 說明 | 追蹤邏輯 |
|-----------|------|----------|
| `paste-cache/{contentHash}.txt` | 貼上內容快取 | history.jsonl 中 `pastedContents.*.contentHash` 引用。**可能被多個 session 共用**，刪除前需檢查引用計數 |
| `projects/{path_hash}/` | 對話記錄，按專案路徑雜湊組織 | 內含 `{session_id}.jsonl` transcript 檔案 |

**paste-cache 共用情況**:

刪除規則: 當刪除某 session 時，若 paste-cache 檔案僅被該 session 引用，則刪除；若被其他 session 引用，則保留。需掃描 history.jsonl 建立引用計數。

**plans 刪除規則**: plans 為 `~/.claude/plans/*.md`。當刪除某 session 時，若 plan 只被該 session 引用（在 history.jsonl 的 display 欄位中）則刪除；若多 session 共用則保留。

#### 不適合按 session 刪除

| 目錄/檔案 | 說明 | 處理方式 |
|-----------|------|----------|
| `backups/.claude.json.backup.*` | 配置備份 | 全域清理，不按 session 處理 |
| `stats-cache.json` | 統計快取 | 全域，不處理 |
| `config.json` / `settings.json` / `settings.local.json` | 全域配置 | 不處理 |

### 2.2 專案本地數據 (.claude/)

每個專案目錄下的 `.claude/` 目錄：

| 檔案/目錄 | 說明 |
|-----------|------|
| `commands/` | 自訂 slash commands |
| `settings.json` | 專案設定 |
| `memory.json` | 專案記憶 |
| `plans/` | 專案相關的 plans |

### 2.3 關聯邏輯

- **Session → 專案**: 透過 `workingDirectory` 關聯 (存於 history.jsonl 的 `project` 欄位)
- **Session ID 格式**: UUID 格式 (e.g., `012e2e2d-fde5-4146-bc11-15a436a8d46b`)
- **Todo 檔名格式**: `{session_id}-agent-{session_id}.json`

---

## 3. 功能規格

### 3.1 列出專案和會話

```
ccsm list [OPTIONS]
```

**輸出範例**:
```
Projects: 2 | Sessions: 4

~/Documents/Dev/FYP-LLM (3 sessions)
 ├── 012e2e2d-fde5-4146-bc11-15a436a8d46b [2024-03-05] ●active
 ├── 2acfdebe-53d1-47de-8563-4614936dada6 [2024-03-05]
 └── 51bd6114-6234-48b1-b03b-598b192eeb78 [2024-03-05]

~/Documents/Dev/Real-Alpha-Trader (1 session)
 └── 67a0789d-d082-4b67-8c74-22dc52cf696c [2024-03-04]

Orphan sessions (no project):
 • 8007497a-c66c-4ff1-8ca2-e4209bf27e26 [2024-03-03]
```

**選項**:
- `--json` - JSON 格式輸出 (適合 CLI 自動化)
- `--project PATH` - 只列出特定專案
- `-v, --verbose` - 顯示更多資訊 (如 task 數量、todo 數量、plan 數量)

### 3.2 刪除特定會話

```
ccsm delete <session_id> [OPTIONS]
```

**刪除範圍**:

直接匹配 (按 session_id 刪除):
1. `~/.claude/tasks/{session_id}/` - 任務資料
2. `~/.claude/todos/*{session_id}*` - 待辦事項
3. `~/.claude/session-env/{session_id}/` - 環境變數
4. `~/.claude/sessions/*.json` - 讀取 JSON 內容，匹配 sessionId 後刪除
5. `~/.claude/file-history/{session_id}/` - 檔案編輯歷史
6. `~/.claude/debug/{session_id}.txt` - 調試日誌
7. `~/.claude/telemetry/1p_failed_events.{session_id}.*.json` - 遙測事件
8. `~/.claude/teams/{session_id}/` - team data directory

間接匹配 (需解析內容或追蹤引用):
9. `~/.claude/paste-cache/{contentHash}.txt` - 需從 history.jsonl 提取 contentHash，並檢查引用計數後才可刪除
10. `~/.claude/plans/*.md` - 掃描 history.jsonl 的 display 欄位；若 plan 只被該 session 引用則刪除，若共用則保留

重寫:
11. `~/.claude/history.jsonl` - 流式處理移除該 session 的紀錄

**選項**:
- `--dry-run` - 預覽要刪除的檔案，不實際刪除
- `-f, --force` - 跳過確認提示（對 active session 也強制刪除）
- `-v, --verbose` - 顯示詳細刪除過程
- `--json` - JSON 格式輸出刪除結果

### 3.3 刪除整個專案

```
ccsm delete-project <project_path> [OPTIONS]
```

**刪除範圍** (專案相關的所有會話 + 可選的專案本地數據):

1. **所有關聯會話**: 該專案的所有 session 資料 (依 3.2 邏輯刪除)

2. **專案本地數據** (可選):
   - 僅在指定 `--include-claude-dir` 時刪除 `{project}/.claude/` 整個目錄

**選項**:
- `--include-claude-dir` - 刪除專案的 `.claude/` 目錄
- `--dry-run` - 預覽
- `-f, --force` - 跳過確認
- `-v, --verbose` - 詳細輸出
- `--json` - JSON 格式輸出刪除結果

### 3.4 查詢會話詳情

```
ccsm info <session_id>
```

**輸出範例**:
```
╭──────────────────────────────────────╮
│ Session Info                         │
├──────────────────────────────────────┤
│ Session ID: 012e2e2d-fde5-4146-bc11- │
│              15a436a8d46b            │
│ Project: ~/Documents/Dev/FYP-LLM     │
│ Status: in_progress                  │
│ Created: 2024-03-05 23:11:00         │
│ Tasks: 3                             │
│ Todos: 0                             │
│ Plans: 1                             │
╰──────────────────────────────────────╯

Files to delete: 5
 • ~/.claude/tasks/012e2e2d-fde5-4146-bc11-15a436a8d46b/
 • ~/.claude/session-env/012e2e2d-fde5-4146-bc11-15a436a8d46b/
 • ...
```

### 3.5 清理懸空資料

```
ccsm cleanup [OPTIONS]
```

**功能**:
- 識別不存在於任何專案中的 session (孤立資料)
- 識別 history.jsonl 中已不存在於資料目錄的過時項目 (stale entries)
- 選項: `--dry-run`, `--auto-remove` (自動刪除孤立資料 + 清理過時 history 項目)
- 其他旗標: `--verbose`, `--json`

### 3.6 互動模式 (TUI)

```
ccsm interactive
# 或簡寫
ccsm -i
```

**功能**:
- 彩色表格顯示專案和會話
- 方向鍵或點擊導航
- 選擇要刪除的項目
- D 鍵刪除選中項目
- Q 鍵退出
- O 鍵切換到 orphan sessions 視圖
- P 鍵切換到 projects 視圖
- R 鍵重新整理

---

## 4. CLI 自動化設計

### 4.1 JSON 輸出格式

```json
{
  "version": "1.0",
  "projects": [
    {
      "path": "/Users/kenc/Documents/Dev/FYP-LLM",
      "sessionCount": 3,
      "sessions": [
        {
          "id": "012e2e2d-fde5-4146-bc11-15a436a8d46b",
          "status": "in_progress",
          "createdAt": "2024-03-05T23:11:00Z",
          "taskCount": 3,
          "planCount": 1
        }
      ]
    }
  ],
  "orphanSessions": [
    {
      "id": "8007497a-c66c-4ff1-8ca2-e4209bf27e26",
      "status": "completed",
      "createdAt": "2024-03-03T10:00:00Z"
    }
  ]
}
```

### 4.2 錯誤處理

| 錯誤碼 | 說明 |
|--------|------|
| `E001` | Session 不存在 |
| `E002` | 專案路徑不存在 |
| `E003` | 刪除失敗 (權限問題) |
| `E004` | Session 正在使用中 (active) |

---

## 5. 技術實現

### 5.1 數據發現邏輯

```python
def discover_sessions():
    # 1. 從 tasks/ 目錄獲取所有 session ID
    session_ids = list_dirs("~/.claude/tasks/")

    # 2. 從 projects/{path_hash}/ 目錄解析 session
    # 路徑格式: ~/.claude/projects/{path_hash}/{session_id}.jsonl

    # 3. 從 history.jsonl 獲取 session → workingDirectory 映射
    session_to_project = parse_history()

    return merge_mappings(session_ids, project_paths, session_to_project)
```

### 5.2 檔案刪除流程

```python
def delete_session(session_id):
    # 直接匹配刪除
    direct_patterns = [
        "~/.claude/tasks/{session_id}/",
        "~/.claude/todos/*{session_id}*",
        "~/.claude/session-env/{session_id}/",
        "~/.claude/file-history/{session_id}/",
        "~/.claude/debug/{session_id}.txt",
        "~/.claude/telemetry/1p_failed_events.{session_id}.*.json",
        "~/.claude/teams/{session_id}/",
    ]

    # sessions/*.json: 讀取 JSON 內容檢查 sessionId
    for sess_file in sessions_dir.glob("*.json"):
        if json.load(sess_file).get("sessionId") == session_id:
            delete(sess_file)

    # plans: 從 history.jsonl 的 display 欄位追蹤引用
    for plan_path, ref_sessions in plan_refs.items():
        if len(ref_sessions) == 1 and session_id in ref_sessions:
            delete(plan_path)

    # paste-cache: 從 history.jsonl 提取 contentHash，檢查引用計數
    for content_hash in paste_hashes:
        ref_count = count_content_hash_references(content_hash)
        if ref_count == 1:  # 僅本 session 引用
            delete(f"~/.claude/paste-cache/{content_hash}.txt")

    # 重寫 history.jsonl 移除該 session
    rewrite_history_remove(session_id)
```

### 5.3 依賴

- Python 3.10+
- 標準庫: `pathlib`, `json`, `os`, `glob`, `argparse`, `tempfile`
- 選用: `rich` (CLI 輸出), `textual` (TUI 介面)

---

## 6. 命令速覽

```bash
# 列出所有專案和會話
ccsm list
ccsm list --json
ccsm list --project "~/Documents/Dev/FYP-LLM"
ccsm list -v

# 查詢會話詳情
ccsm info 012e2e2d-fde5-4146-bc11-15a436a8d46b

# 刪除會話
ccsm delete 012e2e2d-fde5-4146-bc11-15a436a8d46b
ccsm delete 012e2e2d-fde5-4146-bc11-15a436a8d46b --dry-run

# 刪除專案
ccsm delete-project "~/Documents/Dev/FYP-LLM"
ccsm delete-project "~/Documents/Dev/FYP-LLM" --include-claude-dir

# 清理懸空資料
ccsm cleanup
ccsm cleanup --auto-remove

# 啟動互動模式 (TUI)
ccsm interactive
ccsm -i
```

---

## 7. 預設行為

| 場景 | 預設行為 |
|------|----------|
| 刪除 active session | 警告但允許 (可加 --force 跳過) |
| 刪除專案時一併刪除 .claude/ | **需明確指定** `--include-claude-dir` |
| 刪除不存在的 session | 錯誤退出 (E001) |
| history.jsonl 太大 | 流式處理，漸進式重寫 |
| cleanup 時的過時歷史項目 | 自動清理 (當使用 `--auto-remove` 時) |

---

## 8. 未來擴展 (不在本版本範圍)

- [ ] 支援遠程 session 管理 (SSH)
- [ ] Session 匯出/匯入功能
- [ ] 與 MCP 工具整合
- [ ] Session 備份功能
- [ ] 搜尋會話內容