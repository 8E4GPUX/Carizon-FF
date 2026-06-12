#!/bin/bash

# 初始化全局变量
declare -g BASE_DIR="/home/user/fkm/pack"              # 基础工作目录
declare -g MOUNT_POINT="/home/user/10.21.25.201"    # 本地挂载点路径
declare -g NAS_SOURCE="10.21.25.201:/volume1/Data"     # NAS存储源地址
declare -g MCAP_TOOL_DIR="/home/user/fkm/pack/mcap/mcapplayer"  # mcap工具目录
declare -g valid_inputs                                # 声明 valid_inputs 为全局变量
declare -g storage_option                             # 存储选项（1：默认地址，2：用户输入地址）
declare -g user_target_dir                            # 用户输入的目标目录
declare -gA data_storage_map                          # 存储数据ID与存放地址的映射关系
declare -gA data_id_map                              # 存储提取的数据ID与用户原始输入的映射
declare -gA data_type_map                            # 存储数据ID对应的目录类型（pack或mcap）
declare -g NAS_DIR                                    # 声明 NAS_DIR 为全局变量
declare -g OUT_DIR                                    # 声明 OUT_DIR 为全局变量

# 颜色定义
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
NC='\033[0m'
red_echo() { echo -e "\033[31m $*\033[0m"; }     # 错误信息（红色）
green_echo() { echo -e "\033[32m $*\033[0m"; }   # 成功信息（绿色）
yellow_echo() { echo -e "\033[33m $*\033[0m"; }  # 提示信息（黄色）
blue_echo() { echo -e "\033[34m $*\033[0m"; }    # 操作指示（蓝色）

# 挂载状态检查
nas_update(){
    # 强制使用正确的挂载点路径
    local correct_mount_point="/home/user/10.21.25.201"
    
    # 检查是否存在任何包含10.21.25.201的挂载点
    local actual_mount_point=""
    while IFS= read -r line; do
        if [[ $line =~ ^.*10\.21\.25\.[0-9]+.*on.*type.*nfs ]]; then
            # 提取挂载点路径
            actual_mount_point=$(echo "$line" | awk '{print $3}')
            if [ -d "$actual_mount_point" ]; then
                break
            fi
        fi
    done < <(mount -l)

    if [ -n "$actual_mount_point" ]; then
        # 如果检测到的挂载点不是我们想要的，尝试重新挂载到正确位置
        if [ "$actual_mount_point" != "$correct_mount_point" ]; then
            yellow_echo "检测到挂载点：$actual_mount_point，但需要使用：$correct_mount_point"
            # 检查正确路径是否已存在且可访问
            if [ -d "$correct_mount_point" ] && [ -r "$correct_mount_point" ]; then
                MOUNT_POINT="$correct_mount_point"
                green_echo "使用正确的挂载点：$MOUNT_POINT"
            else
                # 尝试重新挂载到正确位置
                yellow_echo "尝试重新挂载到正确位置..."
                echo "123456" | sudo -S mkdir -p "$correct_mount_point" || {
                    red_echo "挂载点创建失败：$correct_mount_point"
                    exit 1
                }
                if echo "123456" | sudo -S mount -t nfs "$NAS_SOURCE" "$correct_mount_point"; then
                    MOUNT_POINT="$correct_mount_point"
                    green_echo "重新挂载成功：$MOUNT_POINT"
                else
                    # 如果重新挂载失败，使用检测到的挂载点
                    MOUNT_POINT="$actual_mount_point"
                    yellow_echo "重新挂载失败，使用检测到的挂载点：$MOUNT_POINT"
                fi
            fi
        else
            MOUNT_POINT="$actual_mount_point"
            green_echo "检测到正确的NAS存储挂载点：$MOUNT_POINT"
        fi
    else
        # 如果没有找到，尝试创建新的挂载点
        if ! mountpoint -q "$correct_mount_point"; then
            sleep 0.2
            yellow_echo "正在挂载NAS存储到：$correct_mount_point"
            echo "123456" | sudo -S mkdir -p "$correct_mount_point" || {
                red_echo "挂载点创建失败：$correct_mount_point"
                exit 1
            }
            if echo "123456" | sudo -S mount -t nfs "$NAS_SOURCE" "$correct_mount_point"; then
                sleep 0.2
                MOUNT_POINT="$correct_mount_point"
                green_echo "NAS存储挂载成功：$MOUNT_POINT"
            else
                red_echo "NAS存储挂载失败，请手动检查！"
                exit 1
            fi
        else
            MOUNT_POINT="$correct_mount_point"
            sleep 0.2
            green_echo "检测到NAS存储已挂载：$MOUNT_POINT"
        fi
    fi
}

# 初始化环境检查
check_dirs() {
    sleep 0.2
    echo -e "${BLUE}====== 初始化数据目录 ======${NC}"
    for dir in "$NAS_DIR" "$OUT_DIR"; do
        if mkdir -p "$dir" 2>/dev/null; then
            sleep 0.2
            echo -e "${GREEN}创建工作目录: $(realpath "$dir")${NC}"
        else
            sleep 0.2
            echo -e "${RED}无法创建目录: $dir${NC}"
            exit 1
        fi
    done
}

# 仓库更新程序
protocol_pull(){
    dir="$HOME/.local/protocol"
    echo "正在拉取 $dir 的更新..."
    if [ -d "$dir" ]; then
        output=$(git -C "$dir" pull 2>&1)
        exit_code=$?

        if [ $exit_code -eq 0 ]; then
            echo -e "Success! The output is as follows: "$output""
        else
            echo -e "Pull failed! Error message: \n"$output""
        fi
    else
        echo -e "${YELLOW}$dir 不存在，跳过仓库更新。${NC}"
    fi
}

# 安全建立软链接
create_links() {
    sleep 0.2
    echo -e "${BLUE}====== 建立数据链接 ======${NC}"
    local link_count=0
    local data_type="$1"  # 接收数据类型参数
    local search_pattern=""
    
    if [[ "$data_type" == "pack" ]]; then
        search_pattern="*pack_*"
        echo -e "${BLUE}正在查找pack_开头的目录...${NC}"
    elif [[ "$data_type" == "mcap" ]]; then
        search_pattern="*mcap_*"
        echo -e "${BLUE}正在查找mcap_开头的目录...${NC}"
    else
        echo -e "${RED}未知的数据类型: $data_type${NC}"
        return 1
    fi

    while IFS= read -r -d '' jj; do
        local link_name="${NAS_DIR}/$(basename "$jj")"
        if [ -e "$link_name" ]; then
            sleep 0.2
            echo -e "${YELLOW}链接已存在: $link_name${NC}"
            continue
        fi
        if ln -s "$jj" "$link_name" 2>/dev/null; then
            sleep 0.2
            echo -e "${GREEN}链接创建成功: $(basename "$link_name")${NC}"
            ((link_count++))
        else
            sleep 0.2
            echo -e "${RED}链接创建失败: $jj${NC}"
        fi
    done < <(find "$original_dir" -type d -name "$search_pattern" -print0)

    [ $link_count -eq 0 ] && echo -e "${YELLOW}未找到有效的${data_type}数据包${NC}"
}

# mcap数据处理函数
process_mcap_data() {
    local data_id="$1"
    local original_input="$2"
    local forward="$3"
    local backward="$4"
    
    echo -e "${BLUE}====== 执行MCAP数据切分 ======${NC}"
    
    # 检查mcap工具目录
    if [ ! -d "$MCAP_TOOL_DIR" ]; then
        echo -e "${RED}MCAP工具目录不存在: $MCAP_TOOL_DIR${NC}"
        return 1
    fi
    
    # 检查可能的mcap工具位置
    local mcap_tool_path=""
    echo -e "${BLUE}正在检查MCAP工具...${NC}"
    
    # 检查bin目录是否存在
    if [ ! -d "$MCAP_TOOL_DIR/bin" ]; then
        echo -e "${RED}bin目录不存在: $MCAP_TOOL_DIR/bin${NC}"
        return 1
    fi
    
    # 按优先级检查工具
    if [ -x "$MCAP_TOOL_DIR/bin/mcap-split" ]; then
        mcap_tool_path="$MCAP_TOOL_DIR/bin/mcap-split"
        echo -e "${GREEN}找到MCAP切分工具: $mcap_tool_path${NC}"
    elif [ -f "$MCAP_TOOL_DIR/bin/mcap-split" ]; then
        mcap_tool_path="$MCAP_TOOL_DIR/bin/mcap-split"
        echo -e "${GREEN}找到MCAP切分工具(需要设置权限): $mcap_tool_path${NC}"
        chmod +x "$mcap_tool_path" 2>/dev/null
    elif [ -x "$MCAP_TOOL_DIR/mcaptools.sh" ]; then
        mcap_tool_path="$MCAP_TOOL_DIR/mcaptools.sh"
        echo -e "${GREEN}找到MCAP工具脚本: $mcap_tool_path${NC}"
    elif [ -f "$MCAP_TOOL_DIR/mcaptools.sh" ]; then
        mcap_tool_path="$MCAP_TOOL_DIR/mcaptools.sh"
        echo -e "${GREEN}找到MCAP工具脚本(需要设置权限): $mcap_tool_path${NC}"
        chmod +x "$mcap_tool_path" 2>/dev/null
    elif [ -x "$MCAP_TOOL_DIR/mcap-split" ]; then
        mcap_tool_path="$MCAP_TOOL_DIR/mcap-split"
        echo -e "${GREEN}找到MCAP切分工具: $mcap_tool_path${NC}"
    else
        echo -e "${RED}MCAP切分工具不存在，检查以下位置：${NC}"
        echo -e "${RED}  - $MCAP_TOOL_DIR/bin/mcap-split${NC}"
        echo -e "${RED}  - $MCAP_TOOL_DIR/mcaptools.sh${NC}"
        echo -e "${RED}  - $MCAP_TOOL_DIR/mcap-split${NC}"
        echo -e "${YELLOW}当前目录内容: $(ls -la $MCAP_TOOL_DIR/ 2>/dev/null || echo '无法访问')${NC}"
        return 1
    fi
    
    # 提取时间信息用于mcap切分
    if [[ "$data_id" =~ ^([A-Za-z0-9]{6})_([0-9]{8})-([0-9]{6})-([0-9]{3})$ ]]; then
        local part1="${BASH_REMATCH[1]}"
        local part2="${BASH_REMATCH[2]}"
        local time_code="${BASH_REMATCH[3]}"
        local part3="${BASH_REMATCH[4]}"
        
        # 转换时间格式为完整时间字符串格式：2025-09-22 16:18:25.155
        # 例如：EN0387_20250922-161825-155 -> "2025-09-22 16:18:25.155"
        # part2="20250922" 格式: YYYYMMDD
        # 年: part2的第1-4位: 2025
        # 月: part2的第5-6位: 09
        # 日: part2的第7-8位: 22
        local year="${part2:0:4}"    # 年份：2025 (第1-4位)
        local month="${part2:4:2}"   # 月份：09 (第5-6位)
        local day="${part2:6:2}"     # 日期：22 (第7-8位)
        local hour="${time_code:0:2}" # 小时：16 (第1-2位)
        local minute="${time_code:2:2}" # 分钟：18 (第3-4位)
        local second="${time_code:4:2}" # 秒：25 (第5-6位)
        local millisecond="$part3"   # 毫秒：155

        local mcap_time="\"${year}-${month}-${day} ${hour}:${minute}:${second}.${millisecond}\""
        
        # 查找mcap目录
        local mcap_dir=$(find "$MOUNT_POINT/${part1}/${part2}" -type d -name "*mcap_*" | head -1)
        if [ -z "$mcap_dir" ]; then
            echo -e "${RED}未找到mcap目录在: $MOUNT_POINT/${part1}/${part2}${NC}"
            return 1
        fi
        
        echo -e "${GREEN}找到MCAP数据目录: $mcap_dir${NC}"

        # 创建临时输出目录（以用户输入名称命名）
        local temp_output_dir="${OUT_DIR}/${original_input}_temp"
        mkdir -p "$temp_output_dir" || {
            echo -e "${RED}无法创建临时输出目录: $temp_output_dir${NC}"
            return 1
        }
        
        # 设置MCAP工具的环境变量
        local mcap_env_setup="export LD_LIBRARY_PATH=../lib:\$LD_LIBRARY_PATH && "
        
        # 构建mcap切分命令 - 修正后的流程
        local mcap_cmd=""
        if [[ "$mcap_tool_path" == *"mcaptools.sh" ]]; then
            # 如果使用mcaptools.sh脚本
            mcap_cmd="cd $MCAP_TOOL_DIR/bin && ${mcap_env_setup}bash ../mcaptools.sh split -id \"$mcap_dir\" -od \"$temp_output_dir\" -tt $mcap_time -fs $forward -bs $backward"
        elif [[ "$mcap_tool_path" == *"bin/mcap-split" ]]; then
            # 如果使用bin目录下的mcap-split - 修正工作目录和环境设置
            mcap_cmd="cd $MCAP_TOOL_DIR/bin && ${mcap_env_setup}./mcap-split -id \"$mcap_dir\" -od \"$temp_output_dir\" -tt $mcap_time -fs $forward -bs $backward"
        else
            # 直接使用mcap-split可执行文件 - 修正工作目录
            mcap_cmd="cd $MCAP_TOOL_DIR/bin && ${mcap_env_setup}./mcap-split -id \"$mcap_dir\" -od \"$temp_output_dir\" -tt $mcap_time -fs $forward -bs $backward"
        fi

        # 验证mcap目录存在且可访问
        if [ ! -d "$mcap_dir" ]; then
            echo -e "${RED}MCAP数据目录不存在: $mcap_dir${NC}"
            return 1
        fi

        # 验证临时输出目录可写
        if ! mkdir -p "$temp_output_dir" 2>/dev/null; then
            echo -e "${RED}无法创建或写入临时输出目录: $temp_output_dir${NC}"
            return 1
        fi
        
        echo -e "${BLUE}执行MCAP切分命令...${NC}"
        echo -e "${YELLOW}使用工具: $mcap_tool_path${NC}"
        echo -e "${YELLOW}库路径设置: ${mcap_env_setup:-无}${NC}"
        echo -e "${YELLOW}时间参数: -tt $mcap_time (完整时间字符串格式)${NC}"
        echo -e "${YELLOW}切分参数: -fs $forward (向前秒数) -bs $backward (向后秒数)${NC}"
        echo -e "${YELLOW}输入数据ID: $original_input${NC}"
        echo -e "${YELLOW}MCAP源目录: $mcap_dir${NC}"

        # 验证输入参数
        if ! [[ "$forward" =~ ^[0-9]+$ ]] || [ "$forward" -le 0 ]; then
            echo -e "${RED}向前切分时间无效: $forward (必须为正整数)${NC}"
            return 1
        fi
        if ! [[ "$backward" =~ ^[0-9]+$ ]] || [ "$backward" -le 0 ]; then
            echo -e "${RED}向后切分时间无效: $backward (必须为正整数)${NC}"
            return 1
        fi

        # 验证lib目录是否存在
        if [ ! -d "$MCAP_TOOL_DIR/lib" ]; then
            echo -e "${YELLOW}警告: lib目录不存在: $MCAP_TOOL_DIR/lib${NC}"
        fi

        # 显示执行命令的完整信息
        echo -e "${BLUE}开始执行MCAP切分...${NC}"
#        echo -e "${YELLOW}完整命令: $mcap_cmd${NC}"

        # 执行命令
        echo -e "${BLUE}执行中...${NC}"

        # 创建一个函数来执行命令并显示输出
        execute_with_monitoring() {
            local temp_file=$(mktemp)
            local error_file=$(mktemp)
            local start_time=$(date +%s)

            # 在后台执行命令，确保实时输出
            # 使用bash -c来执行复合命令，避免stdbuf处理复杂命令的问题
            bash -c "$mcap_cmd" >"$temp_file" 2>"$error_file" &
            local cmd_pid=$!

            # 等待命令完成或超时
            local timeout=600  # 10分钟超时
            local elapsed=0

            while kill -0 $cmd_pid 2>/dev/null && [ $elapsed -lt $timeout ]; do
                sleep 2
                elapsed=$((elapsed + 2))
            done

            # 检查命令是否还在运行
            if kill -0 $cmd_pid 2>/dev/null; then
                # 命令仍在运行，强制终止
                kill -9 $cmd_pid 2>/dev/null
                echo -e "${RED}MCAP数据切分超时（超过10分钟），已强制终止${NC}"
                rm -f "$temp_file" "$error_file"
                return 1
            fi

            # 获取命令退出码
            wait $cmd_pid 2>/dev/null
            local cmd_exit_code=$?

            local end_time=$(date +%s)
            local duration=$((end_time - start_time))

            # 检查是否有错误输出
            if [ -s "$error_file" ]; then
                local error_content=$(cat "$error_file")
                # 检查是否是真正的错误（不包括usage信息）
                if echo "$error_content" | grep -q "Invalid trigger timestamp\|Error\|error\|ERROR\|failed\|FAILED" && ! echo "$error_content" | grep -q "Usage:\|Verison:"; then
                    echo -e "${RED}MCAP数据切分失败！用时: ${duration}秒，退出码: $cmd_exit_code${NC}"
                    echo -e "${YELLOW}错误信息:${NC}"
                    cat "$error_file"
                    echo -e "${YELLOW}执行的命令: $mcap_cmd${NC}"
                    rm -f "$temp_file" "$error_file"
                    return 1
                fi
            fi

            # 检查命令退出码
            if [ $cmd_exit_code -eq 0 ]; then
                echo -e "${GREEN}MCAP数据切分完成！用时: ${duration}秒${NC}"
            else
                echo -e "${RED}MCAP数据切分失败！用时: ${duration}秒，退出码: $cmd_exit_code${NC}"
                if [ -s "$error_file" ]; then
                    echo -e "${YELLOW}错误信息:${NC}"
                    cat "$error_file"
                fi
                echo -e "${YELLOW}执行的命令: $mcap_cmd${NC}"
                rm -f "$temp_file" "$error_file"
                return $cmd_exit_code
            fi

            # 显示执行结果
            if [ -d "$temp_output_dir" ]; then
                local output_files=$(find "$temp_output_dir" -type f 2>/dev/null | wc -l)
                if [ "$output_files" -gt 0 ]; then
                    echo -e "${GREEN}成功生成 $output_files 个文件${NC}"
                    echo -e "${GREEN}输出目录: $temp_output_dir${NC}"
                    # 简化文件显示，只显示总数和几个示例
#                    echo -e "${GREEN}文件示例:${NC}"
#                    find "$temp_output_dir" -type f -exec ls -lh {} \; 2>/dev/null | head -2 || echo "无法列出文件"
                else
                    echo -e "${YELLOW}输出目录为空${NC}"
                fi
            fi

            local final_code=$?
            rm -f "$temp_file" "$error_file"
            return $final_code
        }

        # 执行命令
        if execute_with_monitoring; then
            return 0
        else
            local cmd_exit_code=$?

            # 额外调试信息（仅在严重错误时）
            if [ $cmd_exit_code -eq 127 ]; then
                echo -e "${BLUE}检查依赖库信息:${NC}"
                ldd "$mcap_tool_path" 2>/dev/null | head -5 || echo "无法获取依赖库信息"
            fi

            # 检查临时输出目录
            if [ -d "$temp_output_dir" ]; then
                local output_files=$(find "$temp_output_dir" -type f 2>/dev/null | wc -l)
                if [ "$output_files" -gt 0 ]; then
                    echo -e "${YELLOW}临时输出目录中生成了 $output_files 个文件${NC}"
                    echo -e "${GREEN}生成的文件示例: $(ls -la $temp_output_dir/ 2>/dev/null | head -3)${NC}"
                fi
            fi

            return $cmd_exit_code
        fi
    else
        echo -e "${RED}数据ID格式错误: $data_id${NC}"
        return 1
    fi
}

# pack数据处理函数（原有逻辑）
process_pack_data() {
    local data_id="$1"
    local original_input="$2"
    local forward="$3"
    local backward="$4"
    
    echo -e "${BLUE}====== 执行PACK数据切分 ======${NC}"
    
    if [[ "$data_id" =~ ^([A-Za-z0-9]{6})_([0-9]{8})-([0-9]{6})-([0-9]{3})$ ]]; then
        local part1="${BASH_REMATCH[1]}"
        local part2="${BASH_REMATCH[2]}"
        local time_code="${BASH_REMATCH[3]}"
        local part3="${BASH_REMATCH[4]}"
        local full_time="${part2}-${time_code}"
        local file_name="${original_input}"
        
        # 构建执行命令
        local output_dir="${OUT_DIR}/${file_name}"
        mkdir -p "$output_dir" || {
            echo -e "${RED}无法创建输出目录${NC}"
            return 1
        }

        local bolecmd=(
            "bolepack -slice -T ${full_time}"
            "-a ${forward} -b ${backward}"
            "-o \"${output_dir}\""
            "-r \"${NAS_DIR}\""
            "&& bolepack -convert -packlist2mcap"
            "-o \"${output_dir}/${file_name}.mcap\""
            "\"${output_dir}\""
        )
        
        echo -e "${BLUE}正在运行PACK处理命令...${NC}"
        if eval "${bolecmd[*]}"; then
            echo -e "${GREEN}PACK数据切分已完成！${NC}"
            return 0
        else
            echo -e "${RED}PACK数据切分失败！${NC}"
            return 1
        fi
    else
        echo -e "${RED}数据ID格式错误: $data_id${NC}"
        return 1
    fi
}

# 清理函数
cleanup() {
    local cleaned=0
    for dir in "$NAS_DIR" "$OUT_DIR"; do
        if [ -d "$dir" ]; then
            sleep 0.2
            echo -e "${YELLOW}执行清理目录操作 > > > $dir${NC}"
            rm -rf "$dir" && ((cleaned++))
            sleep 0.2
        fi
    done
    sleep 0.2
    [ $cleaned -ge 1 ] && echo -e "${GREEN}清理操作已完成！${NC}"
}

# 输入验证函数
validate_input() {
    # 数据地址验证
    local path_retry=0
    declare -A unique_inputs    # 使用关联数组进行去重
    local total_retry=0
    while true; do
        read -e -p "请输入切分数据ID：" input_paths
        IFS=' ' read -ra inputs <<< "$input_paths"
        if [ ${#inputs[@]} -eq 0 ]; then
            ((path_retry++))
            [ $path_retry -ge 3 ] && { echo -e "${RED}连续3次输入错误，程序终止${NC}"; exit 1; }
            echo -e "${YELLOW}未输入任何数据ID，剩余尝试次数: $((3 - path_retry))${NC}"
            continue
        fi

        for input_path in "${inputs[@]}"; do
            local unix_input="${input_path//\\//}"
            local input_part=$(echo "$unix_input" | xargs)
            if [[ "$input_part" =~ ([A-Za-z0-9]{6}_[0-9]{8}-[0-9]{6}-[0-9]{3}) ]]; then
                # 数据匹配正则表达式
                data_id="${BASH_REMATCH[1]}"
                unique_inputs["$data_id"]="$input_part"  # 利用关联数组的键唯一性进行去重
                data_id_map["$data_id"]="$input_part"    # 存储映射关系
                
                # 检测数据类型（pack或mcap）
                part1="${data_id:0:6}"
                part2="${data_id:7:8}"
                check_dir="$MOUNT_POINT/${part1}/${part2}"

                if [ -d "$check_dir" ]; then
                    # 检查是否存在pack_开头的目录
                    if find "$check_dir" -type d -name "*pack_*" -print -quit | grep -q .; then
                        data_type_map["$data_id"]="pack"
                        echo -e "${GREEN}检测到pack类型数据: $data_id${NC}"
                    # 检查是否存在mcap_开头的目录
                    elif find "$check_dir" -type d -name "*mcap_*" -print -quit | grep -q .; then
                        data_type_map["$data_id"]="mcap"
                        echo -e "${GREEN}检测到mcap类型数据: $data_id${NC}"
                    else
                        echo -e "${YELLOW}警告: $data_id 目录下未找到pack_或mcap_开头的目录${NC}"
                        data_type_map["$data_id"]="unknown"
                    fi
                else
                    echo -e "${YELLOW}警告: 目录不存在 $check_dir${NC}"
                    data_type_map["$data_id"]="unknown"
                fi
            else
                ((total_retry++))
                if [ $total_retry -ge 3 ]; then
                    echo -e "${RED}连续3个输入不符合格式，程序终止${NC}"
                    exit 1
                fi
                echo -e "${YELLOW}输入格式错误: $input_part${NC}"
            fi
        done

        if [ ${#unique_inputs[@]} -gt 0 ]; then
            echo -e "${GREEN}识别到${#unique_inputs[@]}个符合要求的且不重复的数据ID${NC}"
            break
        else
            ((path_retry++))
            [ $path_retry -ge 3 ] && { echo -e "${RED}未输入任何有效数据ID，程序终止${NC}"; exit 1; }
            echo -e "${YELLOW}未找到有效数据ID，剩余尝试次数: $((3 - path_retry))${NC}"
        fi
    done

    # 将唯一的数据ID存储到全局数组 valid_inputs 中
    valid_inputs=("${!unique_inputs[@]}")

    # 时间参数验证
    local time_retry=0
    while true; do
        read -e -p "请输入切分数据向前时间：" forward
        read -e -p "请输入切分数据向后时间：" backward

        if [[ "$forward" =~ ^[0-9]+$ && "$backward" =~ ^[0-9]+$ ]] &&
           [ "$forward" -gt 0 -a "$backward" -gt 0 ]; then
            break
        else
            ((time_retry++))
            [ $time_retry -ge 3 ] && { echo -e "${RED}连续3次输入错误，程序终止${NC}"; exit 1; }
            echo -e "${YELLOW}输入错误，剩余尝试次数: $((3 - time_retry))${NC}"
        fi
    done

    # 存储地址选项
    local storage_retry=0
    while true; do
        read -e -p "请选择切分后数据上传的地址（1：默认地址，2：用户输入地址）： " storage_option
        if [[ "$storage_option" == "1" || "$storage_option" == "2" ]]; then
            break
        else
            ((storage_retry++))
            [ $storage_retry -ge 3 ] && { echo -e "${RED}连续3次输入错误，程序终止${NC}"; exit 1; }
            echo -e "${YELLOW}输入错误，剩余尝试次数: $((3 - storage_retry))${NC}"
        fi
    done

    if [[ "$storage_option" == "2" ]]; then
        # 询问用户输入的目录
        local dir_retry=0
        while true; do
            read -e -p "请输入数据上传的地址： " user_input_dir
            user_input_dir=$(echo "$user_input_dir" | xargs)
            if [[ -n "$user_input_dir" ]]; then
                # 创建目录（如果不存在）
                if [ ! -d "$user_input_dir" ]; then
                    sleep 0.2
                    echo -e "${YELLOW}创建目录: $user_input_dir${NC}"
                    echo "123456" sudo -S mkdir -p "$user_input_dir" || { echo -e "${RED}无法创建目录: $user_input_dir${NC}"; exit 1; }
                fi
                user_target_dir="$user_input_dir"
                break
            else
                ((dir_retry++))
                [ $dir_retry -ge 3 ] && { echo -e "${RED}连续3次输入错误，程序终止${NC}"; exit 1; }
                echo -e "${YELLOW}输入错误，目录不能为空，剩余尝试次数: $((3 - dir_retry))${NC}"
            fi
        done
    fi
}

# 主执行流程
main() {
    # 检查基础目录是否存在
    if [ ! -d "$BASE_DIR" ]; then
        echo -e "${RED}错误：基础工作目录 $BASE_DIR 不存在${NC}"
        exit 1
    fi

    nas_update
    validate_input
    protocol_pull

    local slicing_start_time=$(date +%s)  # 开始时间

    for data_id in "${valid_inputs[@]}"; do
        # 使用提取的有效数据ID，但在命名时使用用户的原始输入
        original_input="${data_id_map[$data_id]}"
        data_type="${data_type_map[$data_id]}"

        # 跳过未知类型的数据
        if [[ "$data_type" == "unknown" ]]; then
            echo -e "${YELLOW}跳过未知类型数据: $data_id${NC}"
            continue
        fi

        echo -e "${BLUE}====== 开始处理数据: $data_id (类型: $data_type) ======${NC}"

        # Set variables for each data
        RUN_ID=$(date +%s%N | sha1sum | head -c 8)
        NAS_DIR="${BASE_DIR}/nas/${RUN_ID}"
        OUT_DIR="${BASE_DIR}/out/${RUN_ID}"   # 使用绝对路径

        check_dirs
        
        # 输出目录信息供Python GUI识别
        echo "NAS_DIR: $NAS_DIR"
        echo "OUT_DIR: $OUT_DIR"
        
        trap 'cleanup' EXIT   # 添加 trap，确保异常退出时执行清理

        input_part="$data_id"
        if [[ "$input_part" =~ ^([A-Za-z0-9]{6})_([0-9]{8})-([0-9]{6})-([0-9]{3})$ ]]; then
            part1="${BASH_REMATCH[1]}"
            part2="${BASH_REMATCH[2]}"
            time_code="${BASH_REMATCH[3]}"
            part3="${BASH_REMATCH[4]}"
            full_time="${part2}-${time_code}"
            # 使用用户原始输入进行命名
            file_name="${original_input}"
            # 修改 original_dir 路径，支持多层目录结构查找和时间戳匹配
            # 先尝试原始路径
            original_dir="$MOUNT_POINT/${part1}/${part2}"
            
            # 如果原始路径不存在，尝试查找 Original 子目录
            if [ ! -d "$original_dir" ]; then
                echo -e "${YELLOW}原始路径不存在，尝试查找 Original 子目录...${NC}"
                # 查找 Original 目录下的数据
                original_candidates=($(find "$MOUNT_POINT/${part1}/${part2}" -type d -name "Original" 2>/dev/null))
                if [ ${#original_candidates[@]} -gt 0 ]; then
                    # 在 Original 目录下查找包含 pack 或 mcap 的目录
                    for orig_dir in "${original_candidates[@]}"; do
                        if find "$orig_dir" -type d \( -name "*pack_*" -o -name "*mcap_*" \) -print0 | grep -q .; then
                            original_dir="$orig_dir"
                            echo -e "${GREEN}找到数据目录: $original_dir${NC}"
                            break
                        fi
                    done
                fi
            fi
            
            # 进一步查找具体的时间戳匹配目录
            if [ -d "$original_dir" ]; then
                # 查找 mcap_ 目录
                mcap_dirs=($(find "$original_dir" -type d -name "mcap_*" 2>/dev/null))
                if [ ${#mcap_dirs[@]} -gt 0 ]; then
                    # 使用第一个找到的 mcap_ 目录
                    mcap_base_dir="${mcap_dirs[0]}"
                    echo -e "${BLUE}找到 mcap 基础目录: $mcap_base_dir${NC}"
                    
                    # 在 mcap_ 目录下查找时间戳匹配的子目录
                    # 数据ID时间格式: YYYYMMDD-HHMMSS，需要匹配到具体的子目录
                    # 例如: CU7639_20250922-185504-591 -> 匹配 20250922-185211_697
                    target_time="${part2}-${time_code}"  # 20250922-185504
                    echo -e "${BLUE}目标时间戳: $target_time${NC}"
                    
                    # 查找所有时间戳子目录
                    time_dirs=($(find "$mcap_base_dir" -maxdepth 1 -type d -name "${part2}-*" 2>/dev/null | sort))
                    if [ ${#time_dirs[@]} -gt 0 ]; then
                        matched_dir=""
                        # 简化的时间匹配：找到最接近目标时间的目录
                        target_hour_min="${time_code:0:4}"  # HHMM
                        target_sec="${time_code:4:2}"      # SS
                        
                        echo -e "${BLUE}目标时间: ${target_hour_min}:${target_sec}${NC}"
                        
                        for time_dir in "${time_dirs[@]}"; do
                            dir_name=$(basename "$time_dir")
                            # 提取目录的开始时间 (格式: YYYYMMDD-HHMMSS_XXX)
                            if [[ "$dir_name" =~ ^([0-9]{8}-[0-9]{6})_ ]]; then
                                dir_start_time="${BASH_REMATCH[1]}"
                                dir_hour_min="${dir_start_time:9:4}"  # HHMM
                                dir_sec="${dir_start_time:13:2}"      # SS
                                
                                echo -e "${BLUE}检查目录: $dir_name (${dir_hour_min}:${dir_sec})${NC}"
                                
                                # 简单匹配：小时分钟相同，或者目标时间在目录时间范围内（5分钟窗口）
                                if [ "$target_hour_min" = "$dir_hour_min" ]; then
                                    matched_dir="$time_dir"
                                    echo -e "${GREEN}时间戳匹配成功: $dir_name (小时分钟匹配)${NC}"
                                    break
                                elif [ $((10#$target_hour_min)) -ge $((10#$dir_hour_min)) ] && [ $((10#$target_hour_min)) -lt $((10#$dir_hour_min + 5)) ]; then
                                    matched_dir="$time_dir"
                                    echo -e "${GREEN}时间戳匹配成功: $dir_name (5分钟窗口匹配)${NC}"
                                    break
                                fi
                            fi
                        done
                        
                        if [ -n "$matched_dir" ]; then
                            original_dir="$matched_dir"
                            echo -e "${GREEN}最终数据目录: $original_dir${NC}"
                        else
                            echo -e "${YELLOW}未找到匹配的时间戳目录，使用 mcap 基础目录: $mcap_base_dir${NC}"
                            original_dir="$mcap_base_dir"
                        fi
                    else
                        echo -e "${YELLOW}未找到时间戳子目录，使用 mcap 基础目录: $mcap_base_dir${NC}"
                        original_dir="$mcap_base_dir"
                    fi
                fi
            fi

            if [ -d "$original_dir" ]; then
                sleep 0.2
                echo -e "${GREEN}数据目录有效: $original_dir${NC}"
            else
                sleep 0.2
                echo -e "${RED}目标目录不存在: $original_dir${NC}"
                cleanup  # 清理并继续下一个数据ID
                continue
            fi
        else
            sleep 0.2
            echo -e "${RED}数据ID不匹配正则表达式：$input_part${NC}"
            cleanup  # 清理并继续下一个数据ID
            continue
        fi

        # 根据数据类型选择不同的处理方式
        if [[ "$data_type" == "pack" ]]; then
            # 处理pack类型数据（原有逻辑）
            create_links "pack"
        sleep 0.2
        echo -e "时间范围: 向前 ${GREEN}${forward}秒${NC}  向后 ${GREEN}${backward}秒${NC}"
        sleep 0.2

            if ! process_pack_data "$data_id" "$original_input" "$forward" "$backward"; then
                echo -e "${RED}PACK数据处理失败，跳过该数据${NC}"
                cleanup
                continue
            fi

        elif [[ "$data_type" == "mcap" ]]; then
            # 处理mcap类型数据（新增逻辑）
        sleep 0.2
            echo -e "时间范围: 向前 ${GREEN}${forward}秒${NC}  向后 ${GREEN}${backward}秒${NC}"
            echo -e "MCAP时间格式: ${BLUE}${year}-${month}-${day} ${hour}:${minute}:${second}.${millisecond}${NC} (完整时间字符串格式)"
            echo -e "${BLUE}数据源目录: $MOUNT_POINT/${part1}/${part2}${NC}"
            echo -e "${BLUE}临时输出目录: ${OUT_DIR}/${original_input}_temp${NC}"
            echo -e "${BLUE}最终数据目录: ${OUT_DIR}/${original_input}${NC}"
            sleep 0.2

            # 验证时间参数
            if ! [[ "$forward" =~ ^[0-9]+$ ]] || [ "$forward" -le 0 ]; then
                echo -e "${RED}错误：向前切分时间无效: $forward (必须为正整数)${NC}"
                cleanup
                continue
            fi
            if ! [[ "$backward" =~ ^[0-9]+$ ]] || [ "$backward" -le 0 ]; then
                echo -e "${RED}错误：向后切分时间无效: $backward (必须为正整数)${NC}"
                cleanup
                continue
            fi

            if ! process_mcap_data "$data_id" "$original_input" "$forward" "$backward"; then
                echo -e "${RED}MCAP数据处理失败，跳过该数据${NC}"
                cleanup
                continue
            fi
        else
            echo -e "${RED}未支持的数据类型: $data_type${NC}"
            cleanup
            continue
        fi

        # 数据传输和目录管理
        sleep 0.2
        echo -e "${BLUE}====== 执行数据传输和目录管理 ======${NC}"

        # 定义临时输出目录（MCAP数据已存放在此）
        local temp_output_dir="${OUT_DIR}/${original_input}_temp"

        # 创建以用户输入名称命名的最终目录
        local final_data_dir="${OUT_DIR}/${original_input}"

        if [[ "$storage_option" == "1" ]]; then
            local target_dir="$MOUNT_POINT/${part1}/${part2}/out/"
        elif [[ "$storage_option" == "2" ]]; then
            local target_dir="${user_target_dir}"
        else
            echo -e "${RED}未知的存储选项: $storage_option${NC}"
            cleanup; continue
        fi

        # 检查临时输出目录是否存在
        if [ ! -d "$temp_output_dir" ]; then
            echo -e "${RED}临时输出目录不存在: $temp_output_dir${NC}"
            cleanup; continue
        fi

        # 创建最终数据目录
        mkdir -p "$final_data_dir" || {
            echo -e "${RED}无法创建最终数据目录: $final_data_dir${NC}"
            cleanup; continue
        }

        # 将临时目录中的数据移动到最终目录
        if [ -d "$temp_output_dir" ]; then
            local file_count=$(find "$temp_output_dir" -type f 2>/dev/null | wc -l)
            if [ "$file_count" -gt 0 ]; then
                if mv "$temp_output_dir"/* "$final_data_dir/" 2>/dev/null; then
                    echo -e "${GREEN}数据已移动到最终目录: $final_data_dir (共 $file_count 个文件)${NC}"
                else
                    echo -e "${YELLOW}移动数据时出现问题，将尝试复制${NC}"
                    if cp -r "$temp_output_dir"/* "$final_data_dir/" 2>/dev/null; then
                        echo -e "${GREEN}数据已复制到最终目录: $final_data_dir${NC}"
                    else
                        echo -e "${RED}无法移动或复制数据到最终目录${NC}"
                    fi
                fi
            else
                echo -e "${YELLOW}临时目录中没有找到文件: $temp_output_dir${NC}"
            fi
        else
            echo -e "${YELLOW}临时目录不存在: $temp_output_dir${NC}"
        fi

        # 创建目标目录
        echo "123456" | sudo -S mkdir -p "${target_dir}" || {
            echo -e "${RED}无法创建目标目录: ${target_dir}${NC}"
            cleanup; continue
        }
        sleep 1

        # 执行数据传输到用户指定位置
        if echo "123456" | sudo -S cp --preserve=timestamps -r "$final_data_dir" "$target_dir"; then
            sleep 0.2
            echo -e "${GREEN}切分数据传输已完成：${original_input}${NC}"
            sleep 0.2
            echo -e "${GREEN}数据已存放至: ${target_dir}${original_input}${NC}"
            sleep 0.2
            data_storage_map["$original_input"]="${target_dir}/${original_input}"
        else
            sleep 0.2
            echo -e "${YELLOW}复制操作失败，请检查权限或路径${NC}"
        fi

        cleanup  # 清理当前数据ID的临时文件
        trap - EXIT   # 清除当前的 trap
    done

    local slicing_end_time=$(date +%s)
    local duration=$((slicing_end_time - slicing_start_time))

    echo -e "${GREEN}本次共切分：${#data_storage_map[@]} 个数据${NC}"
    echo -e "${GREEN}切分总用时: ${duration}秒${NC}"
}

# 启动主程序
main

