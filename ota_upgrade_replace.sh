#!/usr/bin/env bash

set -Eeuo pipefail

# =========================
# 可配置项
# =========================
TARGET_IP=""
TARGET_USER="root"
TARGET_HOST=""
REMOTE_OTA_DIR="/ota"
REMOTE_APP_DIR="/app"
MIN_EXTRA_KB=102400   # 额外预留 100MB 空间
SSH_TIMEOUT=8
REBOOT_OFFLINE_WAIT=60
REBOOT_ONLINE_WAIT=300

SSH_OPTS=(
  -o ConnectTimeout="${SSH_TIMEOUT}"
  -o StrictHostKeyChecking=accept-new
)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

on_error() {
  echo "[ERROR] 脚本执行失败：第 ${1} 行，命令：${2}" >&2
}
trap 'on_error "${LINENO}" "${BASH_COMMAND}"' ERR

log() {
  echo "[INFO] $*"
}

warn() {
  echo "[WARN] $*"
}

die() {
  echo "[FATAL] $*" >&2
  exit 1
}

check_local_tools() {
  local tools=(ssh scp unzip awk stat ip)
  for t in "${tools[@]}"; do
    command -v "${t}" >/dev/null 2>&1 || die "本机缺少命令：${t}"
  done
}

resolve_target_ip_by_vehicle_ip() {
  local -a local_ips
  local found=""

  # 优先使用 ip 命令读取全局 IPv4 地址
  mapfile -t local_ips < <(ip -o -4 addr show scope global | awk '{print $4}' | cut -d/ -f1)

  if (( ${#local_ips[@]} == 0 )); then
    die "未查询到本机 IPv4 地址，无法根据自车 IP 选择目标升级 IP。"
  fi

  for found in "${local_ips[@]}"; do
    case "${found}" in
      172.31.48.102)
        TARGET_IP="172.31.48.9"
        ;;
      192.168.2.102)
        TARGET_IP="192.168.2.62"
        ;;
      172.20.1.102)
        TARGET_IP="172.20.1.22"
        ;;
      192.168.62.102)
        TARGET_IP="192.168.62.62"
        ;;
      *)
        continue
        ;;
    esac
    break
  done

  if [[ -z "${TARGET_IP}" ]]; then
    die "未匹配到自车 IP（期望 172.31.48.102 / 192.168.2.102 / 172.20.1.102 / 192.168.62.102）。当前检测到: ${local_ips[*]}"
  fi

  TARGET_HOST="${TARGET_USER}@${TARGET_IP}"
  log "检测到自车 IP：${found}，本次升级目标 IP：${TARGET_IP}"
}

check_ssh_connection() {
  log "检查 SSH 连通性：${TARGET_HOST}"
  ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" "echo '[REMOTE] SSH 连接正常'" >/dev/null
}

list_packages() {
  find "${SCRIPT_DIR}" -maxdepth 1 -type f \( -iname "*.zip" \) -printf "%f\n" | sort
}

classify_package() {
  local pkg="$1"
  local lower
  lower="$(echo "${pkg}" | tr '[:upper:]' '[:lower:]')"

  # MCU 包：特殊升级流程
  if [[ "${lower}" == *"mcu"* ]]; then
    echo "mcu|mcu"
    return
  fi

  # MAP 包：特殊升级流程（关键字 DriveMemoMap）
  if [[ "${lower}" == *"drivememomap"* ]]; then
    echo "map|map"
    return
  fi

  # 整包升级：PVS/VFF/G6
  if [[ "${lower}" == *"pvs"* || "${lower}" == *"vff"* || "${lower}" == *"g6"* ]]; then
    echo "full|full"
    return
  fi

  # 关键字映射到 /app 下同名目录
  local direct_keys=(
    env_model odometry encryption trigger fsd_control guard dsp ipcf_proxy
    para_check planning_node system_monitor dpsm
  )
  local key
  for key in "${direct_keys[@]}"; do
    if [[ "${lower}" == *"${key}"* ]]; then
      echo "app|${key}"
      return
    fi
  done

  # 特殊映射
  if [[ "${lower}" == *"perception"* ]]; then
    echo "app|adas"
    return
  fi

  if [[ "${lower}" == *"calibration"* ]]; then
    echo "app|calib_app"
    return
  fi

  echo "unknown|unknown"
}

get_file_size_kb() {
  local file="$1"
  local bytes
  bytes="$(stat -c%s "${file}")"
  echo $(( (bytes + 1023) / 1024 ))
}

get_remote_ota_avail_kb() {
  ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" "df -Pk ${REMOTE_OTA_DIR} | awk 'NR==2{print \$4}'"
}

check_remote_ota_space() {
  local pkg="$1"
  local local_file="${SCRIPT_DIR}/${pkg}"
  local need_kb avail_kb total_need
  local avail_kb_after

  need_kb="$(get_file_size_kb "${local_file}")"
  avail_kb="$(get_remote_ota_avail_kb)"
  total_need=$(( need_kb + MIN_EXTRA_KB ))

  log "容量检查：包=${pkg}, 包大小=${need_kb}KB, /ota 可用=${avail_kb}KB, 需要>=${total_need}KB"

  if (( avail_kb < total_need )); then
    warn "/ota 空间不足，无法升级 ${pkg}。"
    if confirm "是否立即清理板端 /ota 目录后重试容量检查?"; then
      log "开始清理板端 ${TARGET_HOST}:${REMOTE_OTA_DIR}"
      ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" bash -s -- "${REMOTE_OTA_DIR}" <<'EOF'
set -Eeuo pipefail
ota_dir="$1"
cd "${ota_dir}"
rm -rf -- * .[!.]* ..?* 2>/dev/null || true
echo "[REMOTE] /ota 目录清理完成"
EOF

      avail_kb_after="$(get_remote_ota_avail_kb)"
      log "清理后 /ota 可用空间=${avail_kb_after}KB，需求>=${total_need}KB"
      if (( avail_kb_after < total_need )); then
        warn "清理后空间仍不足，请人工进一步清理。"
        return 1
      fi
      return 0
    fi

    warn "用户取消自动清理，请先手动清理 /ota 后重试。"
    return 1
  fi

  return 0
}

upload_package() {
  local pkg="$1"
  local local_file="${SCRIPT_DIR}/${pkg}"

  log "上传压缩包到 ${TARGET_HOST}:${REMOTE_OTA_DIR}/${pkg}"
  scp "${SSH_OPTS[@]}" "${local_file}" "${TARGET_HOST}:${REMOTE_OTA_DIR}/"
}

kind_requires_reboot_wait() {
  local kind="$1"
  case "${kind}" in
    app|map|full)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

wait_for_device_online_between_packages() {
  local i

  log "检测到多包连续升级，等待设备离线并重新上线后继续..."

  for ((i=1; i<=REBOOT_OFFLINE_WAIT; i++)); do
    if ! ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" "echo ok" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  for ((i=1; i<=REBOOT_ONLINE_WAIT; i++)); do
    if ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" "echo '[REMOTE] online'" >/dev/null 2>&1; then
      log "设备已上线，继续下一个包。"
      return 0
    fi
    sleep 1
  done

  die "等待设备上线超时，已停止后续升级。"
}

upgrade_app_package() {
  local pkg="$1"
  local target_dir="$2"

  log "开始 APP 替换升级：包=${pkg}, 目标目录=${REMOTE_APP_DIR}/${target_dir}"

  ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" bash -s -- "${pkg}" "${target_dir}" "${REMOTE_OTA_DIR}" "${REMOTE_APP_DIR}" <<'EOF'
set -Eeuo pipefail
pkg="$1"
target_dir="$2"
ota_dir="$3"
app_dir="$4"

ts="$(date +%Y%m%d%H%M%S)"
backup_name="${target_dir}_old_${ts}"

if [[ ! -f "${ota_dir}/${pkg}" ]]; then
  echo "[REMOTE-ERROR] 未找到上传包：${ota_dir}/${pkg}" >&2
  exit 1
fi

mount -o remount rw "${app_dir}"
systemctl daemon-reload

if [[ -e "${app_dir}/${target_dir}" ]]; then
  mv "${app_dir}/${target_dir}" "${ota_dir}/${backup_name}"
  echo "[REMOTE] 已备份 ${app_dir}/${target_dir} -> ${ota_dir}/${backup_name}"
else
  echo "[REMOTE-WARN] 目标目录不存在：${app_dir}/${target_dir}，跳过备份"
fi

cd "${ota_dir}"
unzip -o "${pkg}" -d "${app_dir}"
rm -f "${ota_dir}/${pkg}"
sync

# 用后台方式触发 reboot，避免 SSH 连接被立即中断导致脚本误判
nohup sh -c 'sleep 1; reboot' >/dev/null 2>&1 &
echo "[REMOTE] 替换完成，已执行 sync 并触发 reboot"
EOF
}

upgrade_mcu_package() {
  local pkg="$1"

  log "开始 MCU 升级：包=${pkg}"

  ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" bash -s -- "${pkg}" "${REMOTE_OTA_DIR}" <<'EOF'
set -Eeuo pipefail
pkg="$1"
ota_dir="$2"

if [[ ! -f "${ota_dir}/${pkg}" ]]; then
  echo "[REMOTE-ERROR] 未找到上传包：${ota_dir}/${pkg}" >&2
  exit 1
fi

cd "${ota_dir}"
if command -v ota_tool >/dev/null 2>&1; then
  ota_tool -p "${pkg}:mcu"
else
  echo "[REMOTE-ERROR] 未找到 ota_tool 命令" >&2
  exit 1
fi

echo "[REMOTE] MCU 升级命令执行完成（不执行 sync/reboot）"
EOF
}

upgrade_full_package() {
  local pkg="$1"
  local ssh_rc=0

  log "开始整包升级：包=${pkg}"

  if ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" bash -s -- "${pkg}" "${REMOTE_OTA_DIR}" <<'EOF'
set -Eeuo pipefail
pkg="$1"
ota_dir="$2"

if [[ ! -f "${ota_dir}/${pkg}" ]]; then
  echo "[REMOTE-ERROR] 未找到上传包：${ota_dir}/${pkg}" >&2
  exit 1
fi

cd "${ota_dir}"
if command -v ota_tool >/dev/null 2>&1; then
  ota_tool -p "${pkg}"
else
  echo "[REMOTE-ERROR] 未找到 ota_tool 命令" >&2
  exit 1
fi

echo "[REMOTE] 整包升级命令执行完成"
EOF
  then
    log "整包升级命令执行完成。"
  else
    ssh_rc=$?
    if (( ssh_rc == 255 )); then
      warn "整包升级期间 SSH 连接中断（exit=${ssh_rc}），通常是板端自动重启导致，按成功流程继续。"
    else
      die "整包升级失败，SSH 返回码=${ssh_rc}"
    fi
  fi

}

upgrade_map_package() {
  local pkg="$1"

  log "开始 MAP 升级：包=${pkg}"

  ssh "${SSH_OPTS[@]}" "${TARGET_HOST}" bash -s -- "${pkg}" "${REMOTE_OTA_DIR}" <<'EOF'
set -Eeuo pipefail
pkg="$1"
ota_dir="$2"

if [[ ! -f "${ota_dir}/${pkg}" ]]; then
  echo "[REMOTE-ERROR] 未找到上传包：${ota_dir}/${pkg}" >&2
  exit 1
fi

cd "${ota_dir}"
unzip -o "${pkg}"

if [[ -f "${ota_dir}/map_update.sh9" ]]; then
  chmod +x "${ota_dir}/map_update.sh9"
  bash "${ota_dir}/map_update.sh9"
elif [[ -f "${ota_dir}/map_update.sh" ]]; then
  chmod +x "${ota_dir}/map_update.sh"
  bash "${ota_dir}/map_update.sh"
else
  script_path="$(find "${ota_dir}" -maxdepth 3 -type f \( -name 'map_update.sh9' -o -name 'map_update.sh' \) | head -n 1 || true)"
  if [[ -z "${script_path}" ]]; then
    echo "[REMOTE-ERROR] 未找到 map_update.sh9/map_update.sh" >&2
    exit 1
  fi
  chmod +x "${script_path}"
  bash "${script_path}"
fi

sync

nohup sh -c 'sleep 1; reboot' >/dev/null 2>&1 &
echo "[REMOTE] MAP 升级完成，已执行 sync 并触发 reboot"
EOF
}

confirm() {
  local prompt="$1"
  local ans
  read -r -p "${prompt} [y/N]: " ans
  [[ "${ans}" =~ ^[Yy]$ ]]
}

perform_upgrade() {
  local pkg="$1"
  local kind="$2"
  local target="$3"

  echo
  log "准备处理：${pkg} | 类型=${kind} | 目标=${target}"

  if ! check_remote_ota_space "${pkg}"; then
    return 1
  fi

  upload_package "${pkg}"

  case "${kind}" in
    app)
      upgrade_app_package "${pkg}" "${target}"
      ;;
    mcu)
      upgrade_mcu_package "${pkg}"
      ;;
    map)
      upgrade_map_package "${pkg}"
      ;;
    full)
      upgrade_full_package "${pkg}"
      ;;
    *)
      warn "未知类型，跳过：${pkg}"
      ;;
  esac

  log "处理完成：${pkg}"
}

process_cli_packages() {
  local arg
  local pkg
  local kind
  local target
  local total=0
  local idx=0

  total=$#

  for arg in "$@"; do
    idx=$((idx + 1))
    pkg="$(basename "${arg}")"

    if [[ ! -f "${SCRIPT_DIR}/${pkg}" ]]; then
      die "指定包不存在（需位于脚本目录）：${pkg}"
    fi

    IFS='|' read -r kind target < <(classify_package "${pkg}")
    if [[ "${kind}" == "unknown" ]]; then
      die "指定包无法识别关键字：${pkg}"
    fi

    log "命令行模式升级包：${pkg}"
    perform_upgrade "${pkg}" "${kind}" "${target}"

    if (( total > 1 && idx < total )) && kind_requires_reboot_wait "${kind}"; then
      wait_for_device_online_between_packages
    fi
  done
}

main() {
  check_local_tools
  resolve_target_ip_by_vehicle_ip
  check_ssh_connection

  if (( $# > 0 )); then
    process_cli_packages "$@"
    log "脚本执行结束。"
    return
  fi

  mapfile -t pkgs < <(list_packages)

  if (( ${#pkgs[@]} == 0 )); then
    die "当前目录未找到 zip 压缩包：${SCRIPT_DIR}"
  fi

  local idx=0
  local recognized_count=0
  local recognized_idx=0
  declare -a pkg_names pkg_kinds pkg_targets

  echo "检测到以下压缩包："
  echo "------------------------------------------------------------"
  for p in "${pkgs[@]}"; do
    idx=$((idx + 1))
    IFS='|' read -r kind target < <(classify_package "${p}")
    pkg_names[idx]="${p}"
    pkg_kinds[idx]="${kind}"
    pkg_targets[idx]="${target}"
    if [[ "${kind}" != "unknown" ]]; then
      recognized_count=$((recognized_count + 1))
      recognized_idx="${idx}"
    fi
    printf "%2d) %-45s | type=%-7s | target=%s\n" "${idx}" "${p}" "${kind}" "${target}"
  done
  echo "------------------------------------------------------------"

  if (( recognized_count == 0 )); then
    die "未识别到可升级包，请检查压缩包命名关键字。"
  fi

  if (( recognized_count == 1 )); then
    log "仅识别到 1 个可升级包，直接升级：${pkg_names[recognized_idx]}"
    perform_upgrade "${pkg_names[recognized_idx]}" "${pkg_kinds[recognized_idx]}" "${pkg_targets[recognized_idx]}"
    log "脚本执行结束。"
    return
  fi

  echo "操作选项："
  echo "1) 升级全部安装包（顺序：四合一 -> map -> mcu -> app）"
  echo "2) 升级指定安装包（支持单个或多选）"
  echo "3) 退出"

  local mode
  read -r -p "请选择 [1/2/3]: " mode

  case "${mode}" in
    1)
      local i
      local order_kind
      local -a ordered_pkgs ordered_kinds ordered_targets
      local ordered_total=0
      local ordered_idx

      # 先提示将被跳过的包类型
      for ((i=1; i<=idx; i++)); do
        if [[ "${pkg_kinds[i]}" == "unknown" ]]; then
          warn "跳过未识别包：${pkg_names[i]}"
          continue
        fi
      done

      # 按要求顺序组装：四合一(full) -> map -> mcu -> app
      for order_kind in full map mcu app; do
        for ((i=1; i<=idx; i++)); do
          if [[ "${pkg_kinds[i]}" == "${order_kind}" ]]; then
            ordered_total=$((ordered_total + 1))
            ordered_pkgs[ordered_total]="${pkg_names[i]}"
            ordered_kinds[ordered_total]="${pkg_kinds[i]}"
            ordered_targets[ordered_total]="${pkg_targets[i]}"
          fi
        done
      done

      if (( ordered_total == 0 )); then
        die "未检测到可用于“升级全部”的包（仅支持 full/map/mcu/app）。"
      fi

      for ((ordered_idx=1; ordered_idx<=ordered_total; ordered_idx++)); do
        perform_upgrade "${ordered_pkgs[ordered_idx]}" "${ordered_kinds[ordered_idx]}" "${ordered_targets[ordered_idx]}"
        if (( ordered_idx < ordered_total )) && kind_requires_reboot_wait "${ordered_kinds[ordered_idx]}"; then
          wait_for_device_online_between_packages
        fi
      done
      ;;
    2)
      local choose_list
      local item
      local chosen
      local seen=","
      local -a selected_pkgs selected_kinds selected_targets
      local selected_count=0
      local sidx
      read -r -p "请输入要升级的序号（支持逗号分隔，如 1,3,5）: " choose_list

      if [[ -z "${choose_list//[[:space:]]/}" ]]; then
        die "未输入有效序号。"
      fi

      IFS=',' read -r -a chosen <<< "${choose_list}"
      for item in "${chosen[@]}"; do
        item="${item//[[:space:]]/}"
        if [[ -z "${item}" ]]; then
          continue
        fi
        if [[ ! "${item}" =~ ^[0-9]+$ ]]; then
          die "无效序号：${item}"
        fi
        if [[ -z "${pkg_names[item]:-}" ]]; then
          die "无效序号：${item}"
        fi
        if [[ "${pkg_kinds[item]}" == "unknown" ]]; then
          warn "跳过未识别包：${pkg_names[item]}"
          continue
        fi
        if [[ "${seen}" == *",${item},"* ]]; then
          warn "跳过重复序号：${item}"
          continue
        fi
        seen+="${item},"
        selected_count=$((selected_count + 1))
        selected_pkgs[selected_count]="${pkg_names[item]}"
        selected_kinds[selected_count]="${pkg_kinds[item]}"
        selected_targets[selected_count]="${pkg_targets[item]}"
      done

      if (( selected_count == 0 )); then
        warn "未选择到可升级包。"
      fi

      for ((sidx=1; sidx<=selected_count; sidx++)); do
        perform_upgrade "${selected_pkgs[sidx]}" "${selected_kinds[sidx]}" "${selected_targets[sidx]}"
        if (( selected_count > 1 && sidx < selected_count )) && kind_requires_reboot_wait "${selected_kinds[sidx]}"; then
          wait_for_device_online_between_packages
        fi
      done
      ;;
    3)
      log "已退出。"
      ;;
    *)
      die "无效选项：${mode}"
      ;;
  esac

  log "脚本执行结束。"
}

main "$@"
