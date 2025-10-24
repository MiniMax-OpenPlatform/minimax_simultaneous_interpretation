#!/bin/bash

# GitHub准备脚本 - 清理敏感信息和临时文件

echo "🧹 准备GitHub上传..."

# 删除所有日志文件
echo "删除日志文件..."
find . -name "*.log" -not -path "./.venv/*" -delete

# 删除Python缓存
echo "删除Python缓存..."
find . -name "__pycache__" -not -path "./.venv/*" -type d -exec rm -rf {} + 2>/dev/null

# 删除临时文件
echo "删除临时文件..."
find . -name "*.tmp" -not -path "./.venv/*" -delete
find . -name "*.temp" -not -path "./.venv/*" -delete
find . -name "*.bak" -not -path "./.venv/*" -delete

# 检查是否有硬编码的API key
echo "检查API key..."
if grep -r "sk-" . --exclude-dir=.venv --exclude-dir=.git --exclude="prepare_for_github.sh" --exclude="README.md" 2>/dev/null; then
    echo "⚠️ 警告：发现可能的API key，请检查！"
    exit 1
fi

# 确保敏感文件在.gitignore中
echo "验证.gitignore配置..."
if ! grep -q "\.env" .gitignore; then
    echo "⚠️ 警告：.env文件未在.gitignore中！"
    exit 1
fi

if ! grep -q "\*.pem" .gitignore; then
    echo "⚠️ 警告：SSL证书文件未在.gitignore中！"
    exit 1
fi

# 检查git状态
echo "检查git状态..."
if git status --porcelain | grep -E "\.(pem|key|env)$"; then
    echo "⚠️ 警告：发现敏感文件将被提交！"
    echo "请检查以下文件："
    git status --porcelain | grep -E "\.(pem|key|env)$"
    exit 1
fi

echo "✅ GitHub上传准备完成！"
echo "📋 提交前检查清单："
echo "   ✅ 所有日志文件已删除"
echo "   ✅ Python缓存已清理"
echo "   ✅ 临时文件已删除"
echo "   ✅ 无硬编码API key"
echo "   ✅ 敏感文件已在.gitignore中"
echo ""
echo "🚀 现在可以安全地提交和推送到GitHub："
echo "   git add ."
echo "   git commit -m \"Add MiniMax simultaneous interpretation system\""
echo "   git push origin main"