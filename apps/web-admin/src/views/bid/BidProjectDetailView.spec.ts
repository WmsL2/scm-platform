import { describe, expect, it } from "vitest"
import source from "./BidProjectDetailView.vue?raw"

describe("BidProjectDetailView", () => {
  it("gates each lifecycle action by its state and permission", () => {
    expect(source).toContain('project.value?.status === "IMPORTED"')
    expect(source).toContain('project.value.import_status === "PARSED"')
    expect(source).toContain('auth.hasPermission("bid:match")')
    expect(source).toContain('auth.hasPermission("bid:export")')
    expect(source).toContain('auth.hasPermission("bid:submit")')
    expect(source).toContain('auth.hasPermission("bid:result")')
  })

  it("keeps edit and void permissions while terminal projects expose no lifecycle controls", () => {
    expect(source).toContain('auth.hasPermission("bid:update")')
    expect(source).toContain('auth.hasPermission("bid:void")')
    expect(source).toContain('editableStatuses.includes(project.value?.status ?? "")')
    expect(source).toContain('v-if="canStartMatching"')
    expect(source).toContain('v-if="canRecordResult"')
  })

  it("distinguishes the three project timestamps and uses a dash for missing start time", () => {
    expect(source).toContain('label="开始时间"')
    expect(source).toContain('project.start_at ?? "-"')
    expect(source).toContain('label="投标截止时间"')
    expect(source).toContain('project.deadline_at ?? "-"')
    expect(source).toContain('label="创建时间"')
    expect(source).toContain('project.created_at')
  })

  it("only permits submitted quoted-export files and supports an optional result note", () => {
    expect(source).toContain('file.file_type === "QUOTED_EXPORT"')
    expect(source).toContain('bidApi.submit(id, { submitted_file_id: submitFile.value, note: submitNote.value })')
    expect(source).toContain('ElMessageBox.prompt("备注（可选）"')
  })
})
