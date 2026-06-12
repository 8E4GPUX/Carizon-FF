#!/bin/bash

# 初始化环境检查
check_dirs() {
    for dir in nas out; do
        if [ -d "$dir" ]; then
            echo -e "\033[34m$dir目录已存在：$(realpath "$dir")\033[0m"
        else
            mkdir -p "$dir" && echo -e "\033[32m已创建${dir}目录：$(realpath "$dir")\033[0m"
        fi
    done
}

# 建立软连接
In_vs() {
    echo "建立软连接"
    for ii in $original_dir ; do
        dt=$(echo "$ii" | sed -r "s#.+/(20[23][0-9][01][0-9][0-9][0-9])/.*\$#\1#")
        for jj in $(find "$ii" -type d -name "*pack_${dt}_*") ; do
            if echo "$jj" | grep -Eo "/pack_${dt}_[0-9]{6}$" ; then
                ln -v -s "$jj" nas/
            fi
        done
    done
    echo -e "\033[32m初始化完成！\033[0m"
}

# 记录初始状态到临时文件
record_initial_state() {
    local dir=$1
    local temp_file=$(mktemp)
    if [ -d "$dir" ]; then
        find "$dir" -mindepth 1 -maxdepth 1 > "$temp_file"
    fi
    echo "$temp_file"
}

# 清理生成数据
clean_generated_data() {
    local dir=$1
    local record_file=$2
    if [ -f "$record_file" ]; then
        local current_file=$(mktemp)
        if [ -d "$dir" ]; then
            find "$dir" -mindepth 1 -maxdepth 1 > "$current_file"
            comm -13 "$record_file" "$current_file" | while read -r item; do
                echo -e "\033[33m[清理] 删除生成数据: $item\033[0m"
                rm -rf "$item"
            done
        fi
        rm -f "$current_file"
    fi
}

# 在脚本开始时记录初始状态
nas_record=$(record_initial_state "nas")
out_record=$(record_initial_state "out")

# 设置trap确保退出时清理
trap 'clean_generated_data "nas" "$nas_record"; clean_generated_data "out" "$out_record"; rm -f "$nas_record" "$out_record"' EXIT

# 处理数据地址输入
path_retry=0
while true; do
    read -e -p "请输入数据地址：" input_path
    
    # 数据地址验证
    unix_path="${input_path//\\//}"
    input_part=$(basename "$unix_path" | xargs)

    if [[ "$input_part" =~ ^[[:space:]]*([A-Za-z0-9]{6})_([0-9]{8})-([0-9]{6})-([0-9]{3})$ ]]; then
        part1="${BASH_REMATCH[1]}"
        part2="${BASH_REMATCH[2]}"
        time_code="${BASH_REMATCH[3]}"
        part3="${BASH_REMATCH[4]}"
        full_time="${part2}-${time_code}"
        file_name="${part1}_${part2}-${time_code}-${part3}"
        # 检查Original目录是否存在
        original_dir="$HOME/10.21.25.201/${part1}/${part2}/Original"
        if [ ! -d "$original_dir" ]; then
            echo -e "\033[31m错误：目标目录不存在 → $original_dir\033[0m"
            exit 1
        else
            echo -e "$original_dir 目录存在，执行后续操作中..."
        fi
        break
    else
        ((path_retry++))
        if [ $path_retry -ge 3 ]; then
            echo -e "\033[31m[错误] 连续3次输入错误，程序终止\033[0m"
            exit 1
        fi
        echo -e "\033[33m[提示] 数据地址错误，剩余尝试次数：$((3 - path_retry))\033[0m"
    fi
done

# 建立软连接
In_vs
# 执行目录检查
check_dirs

# 处理时间偏移输入
time_retry=0
while true; do
    read -p "请输入切分时间（如：120 5）：" forward backward
    
    # 时间格式验证
    if [[ "$forward" =~ ^[0-9]+$ && "$backward" =~ ^[0-9]+$ ]] && 
       [ "$forward" -gt 0 -a "$backward" -gt 0 ]; then
        break
    else
        ((time_retry++))
        if [ $time_retry -ge 3 ]; then
            echo -e "\033[31m[错误] 连续3次输入错误，程序终止\033[0m"
            exit 1
        fi
        echo -e "\033[33m[提示] 输入错误，剩余尝试次数：$((3 - time_retry))\033[0m"
    fi
done

echo -e "\033[32m输入验证通过，继续执行后续操作...\033[0m"
echo -e "\033[32m准备数据切分：向前${forward}秒，向后${backward}秒\033[0m"
sleep 1

# 构建动态命令
output_dir="out/${input_part}/"
bolecmd=(
    "bolepack -slice -T ${full_time}"
    "-a ${forward} -b ${backward}"
    "-o \"${output_dir}\""
    "-r nas/ &&"
    "bolepack -convert -packlist2mcap"
    "-o \"${output_dir}${input_part}.mcap\""
    "\"${output_dir}\""
)

echo -e "\n\033[32m====== 执行数据处理命令 ======\033[0m"
echo "执行数据切分命令："
printf "%s " "${bolecmd[@]}"
echo ""
eval "${bolecmd[*]}"

# 执行最终复制并显示路径
target_dir="$HOME/10.21.25.201/${part1}/${part2}/"
absolute_path=$(realpath -m "$target_dir")

echo -e "\n\033[32m=== 执行数据复制 ===\033[0m"
# 获取out目录新增内容
out_current=$(record_initial_state "out")
new_files=$(comm -13 "$out_record" "$out_current" | tr '\n' ' ')
rm -f "$out_current"

if [ -z "$new_files" ]; then
    echo -e "${YELLOW}[警告] 没有检测到新生成的数据${NC}"
else
    # 创建目标目录
    final_target="${target_dir}/out/"
    sudo mkdir -p "$final_target"

    # 打印操作信息
    echo -e "${BLUE}[操作] 正在执行复制操作：${NC}"
    echo "$new_files" | tr ' ' '\n'

    # 复制文件
    if sudo cp -a out/"$file_name" "$final_target"; then
        echo -e "${GREEN}[✔] 数据复制已完成：${NC}"
        echo -e "${GREEN}[✔] 数据地址: $final_target/${ $file_name}${NC}"
    else
        echo -e "${YELLOW}[警告] 复制操作失败，请检查权限或路径${NC}"
    fi
fi

echo -e "\033[32m[✔] 所有操作成功完成！\033[0m"