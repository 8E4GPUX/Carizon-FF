#!/bin/bash

# 初始化全局变量
declare -g BASE_DIR="/home/user/fkm/pack"              # 基础工作目录
declare -g MOUNT_POINT="/home/user/10.21.25.25.201"    # 本地挂载点路径
declare -g NAS_SOURCE="10.21.25.201:/volume1/Data"     # NAS存储源地址
declare -g valid_inputs                                # 声明 valid_inputs 为全局变量
declare -g storage_option                             # 存储选项（1：默认地址，2：用户输入地址）
declare -g user_target_dir                            # 用户输入的目标目录
declare -gA data_storage_map                          # 存储数据ID与存放地址的映射关系
declare -gA data_id_map                              # 存储提取的数据ID与用户原始输入的映射
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
    if ! mountpoint -q "$MOUNT_POINT"; then
        sleep 0.2
        yellow_echo "正在挂载NAS存储..."
        echo "123456" | sudo -S mkdir -p "$MOUNT_POINT" || {
            red_echo "挂载点创建失败：$MOUNT_POINT"
            exit 1
        }
        if echo "123456" | sudo -S mount -t nfs "$NAS_SOURCE" "$MOUNT_POINT"; then
            sleep 0.2
            green_echo "NAS存储挂载成功：$MOUNT_POINT"
        else
            red_echo "NAS存储挂载失败，请手动检查！"
            exit 1
        fi
    else
        sleep 0.2
        green_echo "检测到NAS存储已挂载：$MOUNT_POINT"
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
    done < <(find "$original_dir" -type d -name "*pack_*" -print0)

    [ $link_count -eq 0 ] && echo -e "${YELLOW}未找到有效数据包${NC}"
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

        # Set variables for each data
        RUN_ID=$(date +%s%N | sha1sum | head -c 8)
        NAS_DIR="${BASE_DIR}/nas/${RUN_ID}"
        OUT_DIR="${BASE_DIR}/out/${RUN_ID}"   # 使用绝对路径

        check_dirs
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
            # 修改 original_dir 路径，不再包含具体时间子目录
            original_dir="${HOME}/10.21.25.201/${part1}/${part2}"

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

        create_links
        sleep 0.2
        echo -e "${BLUE}====== 执行数据切分 ======${NC}"
        sleep 0.2
        echo -e "时间范围: 向前 ${GREEN}${forward}秒${NC}  向后 ${GREEN}${backward}秒${NC}"
        sleep 0.2

        # 构建执行命令
        local output_dir="${OUT_DIR}/${file_name}"  # 输出目录为 out/${RUN_ID}/原始输入数据名
        mkdir -p "$output_dir" || { echo -e "${RED}无法创建输出目录${NC}"; cleanup; continue; }

        local bolecmd=(
            "bolepack -slice -T ${full_time}"
            "-a ${forward} -b ${backward}"
            "-o \"${output_dir}\""
            "-r \"${NAS_DIR}\""
            "&& bolepack -convert -packlist2mcap"
            "-o \"${output_dir}/${file_name}.mcap\""
            "\"${output_dir}\""
        )
        sleep 0.2
        echo -e "${BLUE}正在运行处理命令...${NC}"
        sleep 0.2
        if eval "${bolecmd[*]}"; then
            sleep 0.2
            echo -e "\n${GREEN}数据切分已完成！${NC}"
        else
            sleep 0.2
            echo -e "\n${RED}数据切分失败！${NC}"
            cleanup  # 清理并继续下一个数据ID
            continue
        fi

        # 数据复制
        sleep 0.2
        echo -e "${BLUE}====== 执行数据传输 ======${NC}"
        if [[ "$storage_option" == "1" ]]; then
            local target_dir="${HOME}/10.21.25.201/${part1}/${part2}/out/"
        elif [[ "$storage_option" == "2" ]]; then
            local target_dir="${user_target_dir}"
        else
            echo -e "${RED}未知的存储选项: $storage_option${NC}"
            cleanup; continue
        fi
        echo "123456" | sudo -S mkdir -p "${target_dir}" || { echo -e "${RED}无法创建目标目录${NC}"; cleanup; continue; }
        sleep 1
        if echo "123456" | sudo -S cp --preserve=timestamps -r "$output_dir" "$target_dir"; then
            sleep 0.2
            echo -e "${GREEN}切分数据传输已完成：${file_name}${NC}"
            sleep 0.2
            echo -e "${GREEN}切分数据地址: ${target_dir}${file_name}${NC}"
            sleep 0.2
            data_storage_map["$original_input"]="${target_dir}/${file_name}"
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
