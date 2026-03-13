#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一命令入口
提供所有项目分析功能的统一调用接口

v2.0 功能：
- 安全扫描（自动）
- 项目检测（自动）
- AST 解析（自动）
- 依赖分析（自动）
- 审计日志（自动）
- 知识图谱（自动）

v3.0 功能：
- 分层索引 (lazy-indexer)
- 多仓库支持 (multi-repo)
- 团队协作 (team)
- 企业集成 (ci, issue)
- AI 能力 (ai, review)
"""

import os
import sys
import io

# 设置 UTF-8 编码输出（解决 Windows 控制台编码问题）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# 添加脚本目录到路径
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))


def get_project_dir(args) -> str:
    """获取项目目录"""
    if args.project_dir:
        return os.path.abspath(args.project_dir)

    # 尝试从配置读取
    try:
        import config_manager
        workdir = config_manager.get_workdir(str(SCRIPTS_DIR))
        if workdir:
            return workdir
    except:
        pass

    return os.getcwd()


def get_template_for_type(project_type: str) -> str:
    """根据项目类型返回模板路径"""
    type_template_map = {
        'android-app': 'mobile/android.md',
        'ios': 'mobile/ios.md',
        'stm32': 'embedded/mcu.md',
        'esp32': 'embedded/mcu.md',
        'pico': 'embedded/mcu.md',
        'keil': 'embedded/mcu.md',
        'iar': 'embedded/mcu.md',
        'platformio': 'embedded/mcu.md',
        'freertos': 'embedded/rtos.md',
        'zephyr': 'embedded/rtos.md',
        'rt-thread': 'embedded/rtos.md',
        'embedded-linux': 'embedded/linux.md',
        'buildroot': 'embedded/linux.md',
        'yocto': 'embedded/linux.md',
        'openwrt': 'embedded/linux.md',
        'qnx': 'embedded/qnx.md',
        'react': 'web/frontend.md',
        'vue': 'web/frontend.md',
        'angular': 'web/frontend.md',
        'svelte': 'web/frontend.md',
        'nextjs': 'web/frontend.md',
        'nuxt': 'web/frontend.md',
        'django': 'web/backend.md',
        'fastapi': 'web/backend.md',
        'flask': 'web/backend.md',
        'spring': 'web/backend.md',
        'gradle-java': 'web/backend.md',
        'php': 'web/backend.md',
        'scala': 'web/backend.md',
        'electron': 'desktop/desktop.md',
        'qt': 'desktop/desktop.md',
        'tauri': 'desktop/desktop.md',
        'flutter': 'desktop/desktop.md',
        'kotlin-multiplatform': 'desktop/desktop.md',
        'go': 'system/native.md',
        'rust': 'system/native.md',
        'cmake': 'system/native.md',
        'makefile': 'system/native.md',
        'meson': 'system/native.md',
        'bazel': 'system/native.md',
        'dotnet': 'system/native.md',
    }
    return type_template_map.get(project_type, 'project-template.md')


def generate_directory_tree(project_dir: str, max_depth: int = 3) -> str:
    """生成目录结构树"""
    import os
    from pathlib import Path

    project_path = Path(project_dir)
    exclude_dirs = {'.git', 'node_modules', 'venv', '__pycache__', 'build', 'dist', 'target', '.gradle', '.projmeta'}

    lines = []
    for root, dirs, files in os.walk(project_path):
        # 过滤排除目录
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        rel_path = os.path.relpath(root, project_path)
        depth = rel_path.count(os.sep) if rel_path != '.' else 0

        if depth > max_depth:
            continue

        indent = '  ' * depth
        folder_name = os.path.basename(root) if root != project_path else os.path.basename(project_dir)
        lines.append(f"{indent}{folder_name}/")

        for file in files[:10]:  # 限制每目录文件数
            lines.append(f"{indent}  {file}")

        if len(files) > 10:
            lines.append(f"{indent}  ... ({len(files) - 10} more files)")

    return '\n'.join(lines[:50])  # 限制总行数


def cmd_init(args):
    """初始化项目（集成所有功能，自动生成 project.md）"""
    from detector import ProjectDetector
    from template_engine import TemplateEngine
    import config_manager

    project_dir = get_project_dir(args)

    # 检查目录是否存在
    if not os.path.isdir(project_dir):
        print(f"错误: 目录不存在: {project_dir}")
        sys.exit(1)

    result = {
        'project_dir': project_dir,
        'steps': {},
    }

    print(f"正在初始化项目: {project_dir}")

    # Step 1: 安全扫描
    print("\n[1/7] 安全扫描...")
    try:
        from security.sensitive_scanner import SensitiveScanner
        scanner = SensitiveScanner()
        scan_result = scanner.scan(project_dir)

        result['steps']['security'] = {
            'status': 'completed',
            'sensitive_files': len(scan_result.sensitive_files),
            'sensitive_contents': len(scan_result.matches),
            'warnings': [],
        }

        if scan_result.sensitive_files:
            print(f"  ⚠️ 发现 {len(scan_result.sensitive_files)} 个敏感文件")
            for f in scan_result.sensitive_files[:3]:
                print(f"    - {f}")
            result['steps']['security']['warnings'].extend(
                scan_result.sensitive_files[:5]
            )

        if scan_result.matches:
            print(f"  ⚠️ 发现 {len(scan_result.matches)} 处敏感内容")
            for c in scan_result.matches[:3]:
                print(f"    - {c.file_path}:{c.line_number}")

        if not scan_result.sensitive_files and not scan_result.matches:
            print("  ✅ 未发现敏感信息")

    except ImportError as e:
        print(f"  ⚠️ 安全模块不可用: {e}")
        result['steps']['security'] = {'status': 'skipped', 'reason': str(e)}

    # Step 2: 项目检测
    print("\n[2/7] 项目检测...")
    detector = ProjectDetector(project_dir)
    detect_result = detector.detect(enable_ast=True, enable_deps=True)

    result['steps']['detection'] = {
        'status': 'completed',
        'project_type': detect_result.get('project_type', 'unknown'),
        'language': detect_result.get('language', 'unknown'),
        'build_system': detect_result.get('build_system', 'unknown'),
        'scale': detect_result.get('scale', 'small'),
    }

    project_type = detect_result.get('project_type', 'unknown')
    print(f"  项目类型: {project_type}")
    print(f"  语言: {detect_result.get('language', 'unknown')}")
    print(f"  构建系统: {detect_result.get('build_system', 'unknown')}")
    print(f"  规模: {detect_result.get('scale', 'small')}")

    # 合并检测结果
    result.update(detect_result)

    # Step 3: AST 解析结果
    if 'code_structure' in detect_result:
        print("\n[3/7] 代码结构分析...")
        code_struct = detect_result['code_structure']
        result['steps']['ast'] = {
            'status': 'completed',
            'functions': code_struct.get('total_functions', 0),
            'classes': code_struct.get('total_classes', 0),
        }
        print(f"  函数: {code_struct.get('total_functions', 0)}")
        print(f"  类: {code_struct.get('total_classes', 0)}")
    else:
        print("\n[3/7] 代码结构分析... 跳过")
        result['steps']['ast'] = {'status': 'skipped'}

    # Step 4: 依赖分析结果
    if 'dependency_analysis' in detect_result:
        print("\n[4/7] 依赖分析...")
        deps = detect_result['dependency_analysis']
        result['steps']['dependencies'] = {
            'status': 'completed',
            'total': deps.get('total', 0),
            'direct': deps.get('direct', 0),
            'circular': deps.get('circular', 0),
            'conflicts': deps.get('conflicts', 0),
        }
        print(f"  总依赖: {deps.get('total', 0)}")
        print(f"  直接依赖: {deps.get('direct', 0)}")
        if deps.get('circular', 0) > 0:
            print(f"  ⚠️ 循环依赖: {deps.get('circular', 0)}")
        if deps.get('conflicts', 0) > 0:
            print(f"  ⚠️ 版本冲突: {deps.get('conflicts', 0)}")
    else:
        print("\n[4/7] 依赖分析... 跳过")
        result['steps']['dependencies'] = {'status': 'skipped'}

    # Step 5: 加载并渲染模板（新增）
    print("\n[5/7] 生成项目文档...")
    try:
        template_engine = TemplateEngine(project_dir=str(SCRIPTS_DIR.parent))
        template_path = get_template_for_type(project_type)

        # 生成目录结构
        directory_tree = generate_directory_tree(project_dir)

        # 准备模板变量
        modules_list = detect_result.get('modules', [])
        # modules 可能是字符串列表或字典列表，统一处理
        if modules_list and isinstance(modules_list[0], str):
            modules_formatted = '\n'.join([f"| {m} | `{m}` | - |" for m in modules_list[:10]])
        else:
            modules_formatted = '\n'.join([f"| {m.get('name', '')} | `{m.get('path', '')}` | {m.get('description', '')} |" for m in modules_list[:10]]) if modules_list else '| - | - | - |'

        config_files_list = detect_result.get('config_files', [])
        # config_files 可能是字符串列表或字典列表，统一处理
        if config_files_list and isinstance(config_files_list[0], str):
            config_table = '\n'.join([f"| {c} | `{c}` | - |" for c in config_files_list[:10]])
            config_formatted = ', '.join([f"`{c}`" for c in config_files_list[:5]])
        else:
            config_table = '\n'.join([f"| {c.get('key', '')} | `{c.get('file', '')}` | {c.get('description', '')} |" for c in config_files_list[:10]]) if config_files_list else '| - | - | - |'
            config_formatted = ', '.join([f"`{c.get('file', '')}`" for c in config_files_list[:5]]) if config_files_list else '无'

        deps_list = detect_result.get('dependencies', [])
        # dependencies 可能是字符串列表或字典列表，统一处理
        if deps_list and isinstance(deps_list[0], str):
            deps_formatted = '\n'.join([f"| {d} | - | - |" for d in deps_list[:10]])
        else:
            deps_formatted = '\n'.join([f"| {d.get('name', '')} | {d.get('version', '')} | {d.get('purpose', '')} |" for d in deps_list[:10]]) if deps_list else '| - | - | - |'

        template_vars = {
            'NAME': detect_result.get('project_name', Path(project_dir).name),
            'TYPE': project_type,
            'LANGUAGE': detect_result.get('language', 'unknown'),
            'FRAMEWORK': detect_result.get('framework', 'N/A'),
            'BUILD_SYSTEM': detect_result.get('build_system', 'unknown'),
            'TARGET_PLATFORM': detect_result.get('target_platform', 'N/A'),
            'DIRECTORY_TREE': directory_tree,
            'MAIN_ENTRY': detect_result.get('entry_points', ['N/A'])[0] if detect_result.get('entry_points') else 'N/A',
            'OTHER_ENTRIES': '\n'.join([f"- `{e}`" for e in detect_result.get('entry_points', [])[1:5]]) if len(detect_result.get('entry_points', [])) > 1 else '',
            'CORE_MODULES': modules_formatted,
            'UTIL_MODULES': '| - | - | - |',
            'CORE_FEATURES': '\n'.join([f"- {f}" for f in detect_result.get('features', ['待分析'])]) if detect_result.get('features') else '待分析',
            'DEPENDENCIES': deps_formatted,
            'INSTALL_CMD': detect_result.get('build_info', {}).get('install', '请参考项目文档') if isinstance(detect_result.get('build_info'), dict) else '请参考项目文档',
            'BUILD_CMD': detect_result.get('build_info', {}).get('build', '请参考项目文档') if isinstance(detect_result.get('build_info'), dict) else '请参考项目文档',
            'RUN_CMD': detect_result.get('build_info', {}).get('run', '请参考项目文档') if isinstance(detect_result.get('build_info'), dict) else '请参考项目文档',
            'TEST_CMD': detect_result.get('build_info', {}).get('test', '请参考项目文档') if isinstance(detect_result.get('build_info'), dict) else '请参考项目文档',
            'CONFIG_TABLE': config_table,
            'NOTES': '请参考项目 README 或相关文档',
            'CONFIG_FILES': config_formatted,
            'EXTRA_FILES': '',
            'DATE': datetime.now().strftime('%Y-%m-%d %H:%M'),
        }

        # 渲染模板
        project_md = template_engine.render(template_path, template_vars)

        # 输出 project.md
        output_dir = Path(project_dir) / '.projmeta'
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / 'project.md'
        output_file.write_text(project_md, encoding='utf-8')

        result['steps']['document'] = {
            'status': 'completed',
            'output_path': str(output_file),
            'template': template_path,
        }
        print(f"  ✅ 已生成: {output_file}")

    except Exception as e:
        print(f"  ⚠️ 文档生成失败: {e}")
        result['steps']['document'] = {'status': 'failed', 'error': str(e)}

    # Step 6: 保存 workdir 配置（新增）
    print("\n[6/7] 保存配置...")
    try:
        config_manager.set_value(str(SCRIPTS_DIR), 'workdir', project_dir)
        result['steps']['config'] = {'status': 'completed'}
        print(f"  ✅ 已保存 workdir = {project_dir}")
    except Exception as e:
        print(f"  ⚠️ 配置保存失败: {e}")
        result['steps']['config'] = {'status': 'failed', 'error': str(e)}

    # Step 7: 验证输出（新增）
    print("\n[7/7] 验证输出...")
    try:
        from validate_output import OutputValidator
        validator = OutputValidator(project_dir)
        validate_result = validator.validate()
        result['steps']['validation'] = {
            'status': 'completed',
            'valid': validate_result,
        }
        if validate_result:
            print("  ✅ 输出验证通过")
        else:
            print("  ⚠️ 输出验证发现问题，请检查文档格式")
    except Exception as e:
        print(f"  ⚠️ 验证模块不可用: {e}")
        result['steps']['validation'] = {'status': 'skipped', 'reason': str(e)}

    # Step 8: 审计日志
    try:
        from security.audit_logger import AuditLogger
        logger = AuditLogger(project_dir)
        logger.log_operation('init', {
            'project_type': project_type,
            'language': detect_result.get('language'),
            'scale': detect_result.get('scale'),
            'files_scanned': len(detect_result.get('files', [])) if detect_result.get('files') else 0,
        })
        result['steps']['audit'] = {'status': 'completed'}
    except ImportError:
        result['steps']['audit'] = {'status': 'skipped'}

    print("\n✅ 初始化完成!")
    print(f"   项目类型: {project_type}")
    print(f"   输出文件: {output_file if 'output_file' in dir() else '未生成'}")

    if args.output:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    return result


def cmd_scan_security(args):
    """扫描敏感信息"""
    from security.sensitive_scanner import SensitiveScanner

    project_dir = get_project_dir(args)

    # 检查目录是否存在
    if not os.path.isdir(project_dir):
        print(f"错误: 目录不存在: {project_dir}")
        sys.exit(1)

    scanner = SensitiveScanner()
    result = scanner.scan(project_dir)

    output = {
        "project_dir": project_dir,
        "sensitive_files": result.sensitive_files,
        "sensitive_contents": [
            {"file": c.file_path, "line": c.line_number, "type": c.sensitive_type.value, "masked": c.masked}
            for c in result.matches[:20]
        ],
        "total_files": len(result.sensitive_files),
        "total_contents": len(result.matches),
    }

    if hasattr(args, 'mask') and args.mask:
        output["masked_files"] = result.sensitive_files

    print(json.dumps(output, indent=2, ensure_ascii=False))


def cmd_watch(args):
    """启动文件监控"""
    from watcher import ProjectWatcher

    project_dir = get_project_dir(args)
    watcher = ProjectWatcher(project_dir)

    print(f"开始监控: {project_dir}")
    print("按 Ctrl+C 停止")

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\n停止监控")


def cmd_git_changes(args):
    """查看 Git 变更"""
    from utils.git_watcher import GitWatcher

    project_dir = get_project_dir(args)
    watcher = GitWatcher(project_dir)

    if args.type == "uncommitted":
        changes = watcher.get_uncommitted_changes()
        print(json.dumps([{
            'file': c.file_path,
            'type': c.change_type.value,
        } for c in changes], indent=2, ensure_ascii=False))
    elif args.type == "diff" and args.commit:
        changes = watcher.get_diff_files(args.commit)
        print(json.dumps(changes, indent=2, ensure_ascii=False))
    else:
        changes = watcher.get_uncommitted_changes()
        print(json.dumps([{
            'file': c.file_path,
            'type': c.change_type.value,
        } for c in changes], indent=2, ensure_ascii=False))


def cmd_analyze_deps(args):
    """依赖分析"""
    from dependency_analyzer import DependencyAnalyzer

    project_dir = get_project_dir(args)
    analyzer = DependencyAnalyzer(project_dir)
    result = analyzer.analyze()

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_analyze_code(args):
    """代码质量分析"""
    from ai_analyzer import AIAnalyzer

    analyzer = AIAnalyzer()

    if args.file:
        result = analyzer.analyze_file(args.file)
    else:
        project_dir = get_project_dir(args)
        result = analyzer.analyze_project(project_dir)

    print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_parse_ast(args):
    """AST 解析"""
    from ast_parser import ASTParser

    parser = ASTParser()

    if args.file:
        result = parser.parse_file(args.file)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.project:
        result = parser.parse_project(args.project)
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_diagram(args):
    """生成图表"""
    from diagram_generator import DiagramGenerator

    generator = DiagramGenerator()
    project_dir = get_project_dir(args)

    if args.type == "architecture":
        from detector import ProjectDetector
        detector = ProjectDetector(project_dir)
        project_info = detector.detect()
        result = generator.generate_architecture_diagram(project_info)

    elif args.type == "dependency":
        from dependency_analyzer import DependencyAnalyzer
        analyzer = DependencyAnalyzer(project_dir)
        deps = analyzer.analyze()
        result = generator.generate_dependency_graph(deps.get("dependency_tree", {}))

    elif args.type == "sequence":
        # 时序图：基于调用链分析
        if args.function:
            from utils.call_chain_analyzer import CallChainAnalyzer
            analyzer = CallChainAnalyzer(project_dir)
            analyzer.analyze()
            chain = analyzer.get_call_chain(args.function, depth=args.depth or 3)
            # 转换为时序图格式
            calls = []
            def extract_calls(node, visited=None):
                if visited is None:
                    visited = set()
                if not node or node.get('function') in visited:
                    return
                visited.add(node.get('function'))
                for child in node.get('children', []):
                    calls.append({
                        'caller': node.get('function', 'Unknown'),
                        'callee': child.get('function', 'Unknown'),
                        'method': child.get('function', ''),
                        'line': child.get('line', '')
                    })
                    extract_calls(child, visited)
            extract_calls(chain)
            result = generator.generate_sequence_diagram(calls)
        else:
            result = "错误: 时序图需要指定 --function 参数"

    elif args.type == "class":
        # 类图：基于 AST 解析
        if args.class_name:
            from ast_parser import ASTParser
            parser = ASTParser()
            # 查找类定义
            classes = []
            for ext in ['.py', '.java', '.ts', '.js']:
                for file_path in Path(project_dir).rglob(f'*{ext}'):
                    if '.git' in str(file_path) or 'node_modules' in str(file_path):
                        continue
                    try:
                        result = parser.parse_file(str(file_path))
                        for cls in result.get('classes', []):
                            if args.class_name.lower() in cls.get('name', '').lower():
                                classes.append(cls)
                    except:
                        pass
            result = generator.generate_class_diagram(classes)
        else:
            # 解析所有类
            from ast_parser import ASTParser
            parser = ASTParser()
            all_classes = []
            for ext in ['.py', '.java', '.ts', '.js']:
                for file_path in Path(project_dir).rglob(f'*{ext}'):
                    if '.git' in str(file_path) or 'node_modules' in str(file_path):
                        continue
                    try:
                        result = parser.parse_file(str(file_path))
                        all_classes.extend(result.get('classes', []))
                    except:
                        pass
            result = generator.generate_class_diagram(all_classes[:20])

    else:
        result = f"未知图表类型: {args.type}"

    if args.format == "html":
        print(generator.to_html(result, f"{args.type} diagram"))
    else:
        print(generator.wrap_with_mermaid(result))


def cmd_knowledge_graph(args):
    """知识图谱操作"""
    from knowledge_graph import KnowledgeGraph

    project_dir = get_project_dir(args)
    kg = KnowledgeGraph(project_dir)

    if args.action == "link":
        if not args.qa_id or not args.files:
            print("错误: link 需要 --qa-id 和 --files 参数")
            sys.exit(1)
        files = args.files.split(",")
        result = kg.link_qa_to_code(args.qa_id, files)
        print(json.dumps({"success": result}, ensure_ascii=False))

    elif args.action == "outdated":
        result = kg.check_outdated()
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "related":
        if not args.file:
            print("错误: related 需要 --file 参数")
            sys.exit(1)
        result = kg.get_related_qa(args.file)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"未知操作: {args.action}")


def cmd_search_qa(args):
    """搜索问答（语义匹配）"""
    project_dir = get_project_dir(args)

    from qa_doc_manager import search_qa
    results = search_qa(project_dir, args.query)

    print(json.dumps(results, indent=2, ensure_ascii=False))


def cmd_audit_log(args):
    """查看审计日志"""
    from security.audit_logger import AuditLogger

    project_dir = get_project_dir(args)

    # 检查目录是否存在
    if not os.path.isdir(project_dir):
        print(f"错误: 目录不存在: {project_dir}")
        sys.exit(1)

    logger = AuditLogger(project_dir)
    limit = getattr(args, 'limit', 20) or 20

    entries = logger.get_audit_trail(limit=limit)

    if not entries:
        print("暂无审计日志")
        return

    print(f"\n最近 {len(entries)} 条审计日志:\n")
    for entry in entries:
        status = "✓" if entry.success else "✗"
        print(f"[{entry.timestamp}] [{status}] {entry.operation}")
        if entry.details:
            print(f"    详情: {json.dumps(entry.details, ensure_ascii=False)}")
        if entry.error_message:
            print(f"    错误: {entry.error_message}")


# ============== v3.0 Commands ==============

def cmd_index(args):
    """分层索引操作"""
    project_dir = get_project_dir(args)

    from indexer.lazy_indexer import LazyIndexer
    indexer = LazyIndexer(project_dir)

    if args.action == "build":
        print("构建分层索引...")
        l0 = indexer.build_l0_index()
        print(f"L0 索引完成: {l0.total_files} 文件, {l0.total_lines} 行, {l0.build_time:.2f}s")

        if args.level >= 1:
            l1 = indexer.get_l1_index()
            print(f"L1 索引完成: {l1.total_functions} 函数, {l1.total_classes} 类, {l1.build_time:.2f}s")

        if args.level >= 2:
            indexer.warmup_l2(callback=lambda success, result: print(
                f"L2 索引{'成功' if success else '失败'}"
            ))

    elif args.action == "search":
        if not args.query:
            print("错误: search 需要 --query 参数")
            return
        results = indexer.search(args.query)
        for r in results[:20]:
            print(f"- [{r['type']}] {r.get('path', r.get('name', ''))}")

    elif args.action == "stats":
        stats = indexer.get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif args.action == "update":
        # 增量更新
        from utils.git_watcher import GitWatcher
        watcher = GitWatcher(project_dir)
        changes = watcher.get_uncommitted_changes()
        changed_files = [c.file_path for c in changes]

        if changed_files:
            result = indexer.incremental_update(changed_files)
            print(f"更新完成: {result['files_processed']} 文件")
        else:
            print("没有变更文件")


def cmd_multi_repo(args):
    """多仓库操作"""
    project_dir = get_project_dir(args)

    from multi_repo.mono_manager import MonoRepoManager
    manager = MonoRepoManager(project_dir)

    if args.action == "list":
        repos = manager.list_repos()
        for repo in repos:
            print(f"- {repo.name}: {repo.type.value} ({repo.language})")

    elif args.action == "detect":
        detected = manager.detect_repos()
        print(f"检测到 {len(detected)} 个关联仓库:")
        for repo in detected:
            print(f"  - {repo.name}: {repo.type} ({repo.language})")

    elif args.action == "search":
        if not args.query:
            print("错误: search 需要 --query 参数")
            return
        results = manager.cross_repo_search(args.query)
        for r in results[:20]:
            print(f"[{r.repo_name}] {r.file_path}: {r.name} ({r.match_type})")

    elif args.action == "graph":
        print(manager.to_mermaid_graph())

    elif args.action == "sync":
        results = manager.sync_all()
        print(f"同步完成: {len(results['success'])} 成功, {len(results['failed'])} 失败")

    elif args.action == "add":
        if not args.name or not args.path:
            print("错误: add 需要 --name 和 --path 参数")
            return
        repo = manager.add_repo(args.name, args.path, args.type)
        print(f"添加仓库: {repo.name}")


def cmd_team(args):
    """团队协作操作"""
    project_dir = get_project_dir(args)

    if args.action == "stats":
        from team.team_knowledge import TeamKnowledgeBase
        kb = TeamKnowledgeBase(project_dir, args.team)
        stats = kb.get_team_stats(args.team)
        print(json.dumps(stats.to_dict(), indent=2, ensure_ascii=False))

    elif args.action == "share":
        from team.team_knowledge import TeamKnowledgeBase
        kb = TeamKnowledgeBase(project_dir)
        success = kb.share_qa(args.qa_id, args.team, args.author or "system")
        print(f"分享{'成功' if success else '失败'}")

    elif args.action == "import":
        from team.team_knowledge import TeamKnowledgeBase
        kb = TeamKnowledgeBase(project_dir)
        imported = kb.import_team_qa(args.team)
        print(f"导入 {len(imported)} 条问答")

    elif args.action == "search":
        from team.team_knowledge import TeamKnowledgeBase
        kb = TeamKnowledgeBase(project_dir)
        results = kb.search_team_qa(args.query, args.team)
        for qa in results[:10]:
            print(f"- {qa.id}: {qa.question[:50]}...")

    elif args.action == "members":
        from team.team_db import TeamDatabase
        db = TeamDatabase()
        members = db.get_team_members(args.team_id or "")
        for m in members:
            print(f"- {m.get('name')}: {m.get('team_role')}")


def cmd_ci(args):
    """CI/CD 集成操作"""
    project_dir = get_project_dir(args)

    from integration.ci_cd import CICDIntegration
    cicd = CICDIntegration(project_dir)

    if args.action == "analyze-pr":
        from integration.ci_cd import PRInfo
        pr = PRInfo(
            number=args.pr_number,
            title="",
            author="",
            source_branch="",
            target_branch="",
        )
        report = cicd.on_pr_created(pr)
        print(report.to_markdown())

    elif args.action == "generate-config":
        if args.platform == "github":
            print(cicd.generate_github_actions_config())
        elif args.platform == "gitlab":
            print(cicd.generate_gitlab_ci_config())
        else:
            print(f"不支持的平台: {args.platform}")


def cmd_issue(args):
    """Issue 系统集成操作"""
    project_dir = get_project_dir(args)

    from integration.issue_tracker import IssueTrackerIntegration
    tracker = IssueTrackerIntegration(project_dir)

    if args.action == "link":
        success = tracker.link_qa_to_issue(args.qa_id, args.issue_url)
        print(f"关联{'成功' if success else '失败'}")

    elif args.action == "issues":
        issues = tracker.get_qa_issues(args.qa_id)
        print(json.dumps(issues, indent=2))

    elif args.action == "file-issues":
        issues = tracker.get_related_issues(args.file)
        for issue in issues:
            print(f"- {issue.id}: {issue.title}")

    elif args.action == "sync":
        result = tracker.sync_issue_status()
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_ai(args):
    """AI 能力操作"""
    project_dir = get_project_dir(args)

    if args.action == "search":
        from ai.vector_store import VectorStore
        store = VectorStore(project_dir)
        results = store.search_similar(args.query)
        for r in results[:10]:
            print(f"- [{r.score:.3f}] {r.id}: {r.content[:50]}...")

    elif args.action == "build-index":
        from ai.vector_store import VectorStore
        store = VectorStore(project_dir)
        store.build_index()
        stats = store.get_stats()
        print(f"索引完成: {stats.total_chunks} 条记录")

    elif args.action == "complete":
        from ai.code_completion import ProjectAwareCompletion, Position
        completer = ProjectAwareCompletion(project_dir)
        position = Position(file=args.file, line=args.line or 0)
        result = completer.get_completion(args.file, position, args.prefix or "")
        for item in result.items[:10]:
            print(f"- [{item.kind}] {item.text}")

    elif args.action == "stats":
        from ai.vector_store import VectorStore
        store = VectorStore(project_dir)
        stats = store.get_stats()
        print(json.dumps({
            'total_vectors': stats.total_vectors,
            'total_chunks': stats.total_chunks,
            'model': stats.model_name,
        }, indent=2))


def cmd_review(args):
    """代码审查操作"""
    project_dir = get_project_dir(args)

    from integration.code_review import CodeReviewAssistant
    assistant = CodeReviewAssistant(project_dir)

    if args.file:
        suggestions = assistant.review_file(args.file)
        for s in suggestions[:10]:
            print(f"- [{s.severity.value}] {s.file}:{s.line} - {s.message}")
    else:
        # 使用重构顾问
        from ai.refactoring_advisor import RefactoringAdvisor
        advisor = RefactoringAdvisor(project_dir)
        suggestions = advisor.analyze()
        print(f"发现 {len(suggestions)} 条重构建议:")
        for s in suggestions[:10]:
            print(f"- [{s.impact}] {s.type.value}: {s.message}")


def cmd_risk(args):
    """代码风险预测"""
    project_dir = get_project_dir(args)

    from ai.quality_predictor import QualityPredictor
    predictor = QualityPredictor(project_dir)

    if args.file:
        assessment = predictor.predict_risk(args.file)
        print(assessment.to_markdown())
    else:
        summary = predictor.get_project_risk_summary()
        print(json.dumps(summary, indent=2, ensure_ascii=False))


def classify_question(question: str) -> str:
    """自动判断问题分类"""
    question_lower = question.lower()
    keywords = {
        'architecture': ['架构', '设计', '结构', 'architecture', 'design', '分层', '模块划分'],
        'build': ['构建', '编译', '打包', 'build', 'compile', 'make', 'cmake', '安装'],
        'feature': ['功能', '实现', '如何', '怎么', 'how', 'feature', '原理', '流程'],
        'debug': ['错误', '异常', '调试', 'error', 'bug', 'debug', '问题', '为什么', '失败'],
        'api': ['接口', 'API', 'api', 'endpoint', '函数', '参数', '调用'],
        'config': ['配置', '设置', 'config', 'setting', '环境'],
        'module': ['模块', '组件', 'component', 'module', '目录'],
        'process': ['流程', '步骤', '过程', '启动', '初始化', 'process', 'flow'],
    }

    for category, words in keywords.items():
        if any(w in question_lower for w in words):
            return category
    return 'other'


def extract_file_refs(text: str) -> List[str]:
    """从文本中提取文件引用"""
    import re
    # 匹配常见文件路径模式
    patterns = [
        r'[a-zA-Z0-9_/.-]+\.(py|js|ts|tsx|jsx|java|go|rs|c|cpp|h|hpp|cs|swift|kt|md|yaml|yml|json|toml)',
        r'src/[a-zA-Z0-9_/.-]+',
        r'lib/[a-zA-Z0-9_/.-]+',
        r'app/[a-zA-Z0-9_/.-]+',
        r'tests?/[a-zA-Z0-9_/.-]+',
    ]

    files = set()
    for pattern in patterns:
        matches = re.findall(pattern, text)
        files.update(matches)

    return list(files)[:10]  # 限制最多10个


def cmd_qa(args):
    """问答记录操作"""
    project_dir = get_project_dir(args)

    from qa_doc_manager import create_qa_doc, search_qa, list_qa_docs, delete_qa_doc, check_outdated

    # 新增：record 子命令
    if hasattr(args, 'record') and args.record:
        question = args.question
        answer = args.answer

        if not question:
            print("错误: 需要提供 --question 参数")
            sys.exit(1)

        if not answer:
            print("错误: 需要提供 --answer 参数")
            sys.exit(1)

        # 自动判断分类
        category = classify_question(question)

        # 从答案中提取文件引用
        file_refs = extract_file_refs(answer)

        # 创建问答文档
        result = create_qa_doc(
            project_dir,
            question,
            answer,
            file_refs=file_refs,
            tags=args.tags.split(',') if args.tags else None
        )

        if result.get('success'):
            print(f"✅ 问答已记录: {result.get('entry_id')}")
            print(f"   分类: {result.get('category')}")
            print(f"   文档: {result.get('doc_path')}")
            if file_refs:
                print(f"   关联文件: {', '.join(file_refs[:3])}")
        else:
            print(f"❌ 记录失败: {result.get('error')}")

        return

    if args.list:
        # 列出问答
        results = list_qa_docs(project_dir, args.category)
        if results:
            print(f"共有 {len(results)} 条问答:")
            for r in results:
                print(f"  [{r.get('id', '?')}] {r.get('question', '')[:50]}...")
        else:
            print("暂无问答记录")

    elif args.check:
        # 检查过期问答
        result = check_outdated(project_dir)
        if result.get('outdated_count', 0) > 0:
            print(f"发现 {result['outdated_count']} 条过期问答:")
            for item in result.get('outdated', []):
                print(f"  [{item['id']}] {item['question'][:30]}...")
                print(f"    原因: {', '.join(item.get('reasons', []))}")
        else:
            print("✅ 所有问答都是最新的")

    elif args.delete:
        # 删除问答
        result = delete_qa_doc(project_dir, args.delete)
        if result.get('success'):
            print(f"✅ 已删除问答: {args.delete}")
        else:
            print(f"❌ 删除失败: {result.get('error', '未知错误')}")

    elif args.auto:
        # 自动记录最近问答（从临时文件读取）
        temp_file = Path(project_dir) / '.projmeta' / '.last_qa.json'
        if temp_file.exists():
            try:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                question = data.get('question', '')
                answer = data.get('answer', '')
                files = data.get('files', [])
                tags = data.get('tags', [])

                if question and answer:
                    result = create_qa_doc(project_dir, question, answer, files, tags)
                    if result.get('success'):
                        print(f"✅ 已记录问答: {result.get('entry_id')}")
                    else:
                        print(f"❌ 记录失败: {result.get('error')}")
                else:
                    print("没有待记录的问答")
            except Exception as e:
                print(f"读取失败: {e}")
        else:
            print("没有待记录的问答")

    elif args.question:
        # 记录指定问答
        question = args.question
        answer = args.answer or ""
        files = args.files.split(',') if args.files else []
        tags = args.tags.split(',') if args.tags else []

        if not answer:
            print("错误: 需要提供 --answer 或使用 --auto")
            return

        result = create_qa_doc(project_dir, question, answer, files, tags)
        if result.get('success'):
            print(f"✅ 已记录问答: {result.get('entry_id')}")
            print(f"   分类: {result.get('category')}")
            print(f"   文档: {result.get('doc_path')}")
        else:
            print(f"❌ 记录失败: {result.get('error')}")

    elif args.search:
        # 搜索问答
        results = search_qa(project_dir, args.search)
        if results:
            print(f"找到 {len(results)} 条相关问答:")
            for r in results[:10]:
                score = r.get('score', 0)
                print(f"  [{score:.2f}] {r.get('question', '')[:50]}...")
        else:
            print("未找到相关问答")

    else:
        # 显示帮助
        print("用法: qa <project_dir> [选项]")
        print("\n选项:")
        print("  --record             直接记录问答（推荐）")
        print("  --question <问题>    指定问题")
        print("  --answer <答案>      指定答案")
        print("  --tags <标签列表>    标签（逗号分隔）")
        print("  --auto               自动记录最近的问答")
        print("  --files <文件列表>   相关文件（逗号分隔）")
        print("  --search <关键词>    搜索问答")
        print("  --list               列出所有问答")
        print("  --check              检查过期问答")
        print("  --delete <ID>        删除指定问答")
        print("  --category <分类>    分类筛选")
        print("\n示例:")
        print("  qa record --question \"登录功能怎么实现？\" --answer \"通过 AuthService 实现...\"")
        print("  qa --search \"WiFi\"")
        print("  qa --list --category feature")


def save_last_qa(project_dir: str, question: str, answer: str,
                 files: List[str] = None, tags: List[str] = None):
    """保存最近的问答（供自动记录使用）"""
    temp_file = Path(project_dir) / '.projmeta' / '.last_qa.json'
    temp_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        'question': question,
        'answer': answer,
        'files': files or [],
        'tags': tags or [],
        'timestamp': datetime.now().isoformat(),
    }

    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# 导出供其他模块使用
__all__ = ['save_last_qa']


def cmd_config(args):
    """配置管理操作"""
    from config_manager import get_value, set_value, delete_value, show_all, show_schema

    if args.action == "get":
        if not args.key:
            print("错误: 需要指定配置键")
            return
        result = get_value(str(SCRIPTS_DIR), args.key)
        if result.get("success"):
            print(f"{args.key} = {result.get('value')}")
        else:
            print(result.get("error", "获取失败"))

    elif args.action == "set":
        if not args.key or args.value is None:
            print("错误: 需要指定配置键和值")
            return
        result = set_value(str(SCRIPTS_DIR), args.key, args.value)
        if result.get("success"):
            print(f"✅ 已设置 {args.key} = {args.value}")
        else:
            print(f"❌ 设置失败: {result.get('error')}")

    elif args.action == "delete":
        if not args.key:
            print("错误: 需要指定配置键")
            return
        result = delete_value(str(SCRIPTS_DIR), args.key)
        print(f"✅ {result.get('message', '已删除')}")

    elif args.action == "show":
        result = show_all(str(SCRIPTS_DIR))
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "schema":
        result = show_schema()
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_call_chain(args):
    """调用链分析"""
    project_dir = get_project_dir(args)

    from utils.call_chain_analyzer import CallChainAnalyzer

    analyzer = CallChainAnalyzer(project_dir)

    if args.function:
        if args.impact:
            # 影响分析
            result = analyzer.get_impact_analysis(args.function)
        else:
            # 调用链分析
            analyzer.analyze()
            result = analyzer.get_call_chain(args.function, args.depth, args.direction)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # 完整分析
        result = analyzer.analyze()
        summary = result.get('summary', {})
        print(f"分析完成:")
        print(f"  函数总数: {summary.get('total_functions', 0)}")
        print(f"  文件总数: {summary.get('total_files', 0)}")
        print(f"  调用总数: {summary.get('total_calls', 0)}")
        print(f"  耗时: {summary.get('analysis_time', '0s')}")


def cmd_feishu(args):
    """飞书文档集成"""
    project_dir = get_project_dir(args)

    from feishu_doc_manager import (
        generate_update_report,
        check_doc_sync_status,
        generate_doc_content_suggestion,
        FEISHU_CONFIG_KEYS
    )

    if args.action == "report":
        report = generate_update_report(project_dir, args.doc_token)
        print(report)

    elif args.action == "status":
        result = check_doc_sync_status(project_dir, args.doc_token)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.action == "suggest":
        if not args.file or not args.type:
            print("错误: 需要指定 --file 和 --type")
            return
        suggestion = generate_doc_content_suggestion(args.file, args.type)
        print(suggestion)

    elif args.action == "config":
        print("飞书配置项（通过 /set-config 设置）:")
        for key in FEISHU_CONFIG_KEYS:
            print(f"  {key}")


def cmd_cache(args):
    """缓存管理"""
    project_dir = get_project_dir(args)

    from utils.cache_manager import CacheManager

    manager = CacheManager(project_dir)

    if args.action == "check":
        result = manager.check_validity(quick=args.quick)
        if result.get('is_valid'):
            print(f"✅ 缓存有效: {result.get('reason', '')}")
        elif result.get('cache_exists'):
            print(f"⚠️ 缓存需要更新: {result.get('reason', '')}")
            if result.get('changed_files'):
                print(f"   变更文件: {', '.join(result['changed_files'][:5])}")
        else:
            print(f"❌ 缓存不存在或无效")

    elif args.action == "update":
        cache = manager.update(incremental=args.incremental)
        print(f"✅ 缓存已更新")
        print(f"   时间: {cache.timestamp}")
        print(f"   跟踪文件: {len(cache.file_hashes)}")

    elif args.action == "clear":
        manager.clear()
        print("✅ 缓存已清除")

    elif args.action == "info":
        cache = manager.load()
        info = {
            'cache_exists': bool(cache.timestamp),
            'version': cache.version,
            'timestamp': cache.timestamp,
            'files_tracked': len(cache.file_hashes),
            'git_branch': cache.git_status.get('branch', ''),
            'last_commit': cache.git_status.get('last_commit', ''),
        }
        print(json.dumps(info, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(
        description="项目分析工具集",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # init 命令
    p_init = subparsers.add_parser("init", help="初始化项目（集成安全扫描、AST、依赖分析）")
    p_init.add_argument("project_dir", nargs="?", help="项目目录")
    p_init.add_argument("--output", "-o", action="store_true", help="输出详细 JSON")
    p_init.set_defaults(func=cmd_init)

    # scan-security 命令
    p_security = subparsers.add_parser("scan-security", help="扫描敏感信息")
    p_security.add_argument("project_dir", nargs="?", help="项目目录")
    p_security.add_argument("--mask", action="store_true", help="输出脱敏后的内容")
    p_security.add_argument("--json", action="store_true", help="JSON格式输出")
    p_security.set_defaults(func=cmd_scan_security)

    # watch 命令
    p_watch = subparsers.add_parser("watch", help="启动文件监控")
    p_watch.add_argument("project_dir", nargs="?", help="项目目录")
    p_watch.set_defaults(func=cmd_watch)

    # git-changes 命令
    p_git = subparsers.add_parser("git-changes", help="查看 Git 变更")
    p_git.add_argument("project_dir", nargs="?", help="项目目录")
    p_git.add_argument("--type", choices=["uncommitted", "diff"], default="uncommitted", help="变更类型")
    p_git.add_argument("--commit", help="对比的 commit")
    p_git.set_defaults(func=cmd_git_changes)

    # analyze-deps 命令
    p_deps = subparsers.add_parser("analyze-deps", help="依赖分析")
    p_deps.add_argument("project_dir", nargs="?", help="项目目录")
    p_deps.set_defaults(func=cmd_analyze_deps)

    # analyze-code 命令
    p_code = subparsers.add_parser("analyze-code", help="代码质量分析")
    p_code.add_argument("project_dir", nargs="?", help="项目目录")
    p_code.add_argument("--file", "-f", help="分析单个文件")
    p_code.set_defaults(func=cmd_analyze_code)

    # parse-ast 命令
    p_ast = subparsers.add_parser("parse-ast", help="AST 解析")
    p_ast.add_argument("--file", "-f", help="解析单个文件")
    p_ast.add_argument("--project", "-p", help="解析整个项目")
    p_ast.set_defaults(func=cmd_parse_ast)

    # diagram 命令
    p_diagram = subparsers.add_parser("diagram", help="生成图表")
    p_diagram.add_argument("type", choices=["architecture", "sequence", "dependency", "class"], help="图表类型")
    p_diagram.add_argument("project_dir", nargs="?", help="项目目录")
    p_diagram.add_argument("--format", choices=["mermaid", "html"], default="mermaid", help="输出格式")
    p_diagram.add_argument("--function", "-f", help="时序图：指定函数名")
    p_diagram.add_argument("--class-name", "-c", help="类图：指定类名")
    p_diagram.add_argument("--depth", "-d", type=int, default=3, help="分析深度")
    p_diagram.set_defaults(func=cmd_diagram)

    # kg 命令 (知识图谱)
    p_kg = subparsers.add_parser("kg", help="知识图谱操作")
    p_kg.add_argument("action", choices=["link", "outdated", "related"], help="操作类型")
    p_kg.add_argument("project_dir", nargs="?", help="项目目录")
    p_kg.add_argument("--qa-id", help="问答 ID")
    p_kg.add_argument("--files", help="文件列表（逗号分隔）")
    p_kg.add_argument("--file", help="单个文件")
    p_kg.set_defaults(func=cmd_knowledge_graph)

    # search-qa 命令
    p_search = subparsers.add_parser("search-qa", help="搜索问答")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("project_dir", nargs="?", help="项目目录")
    p_search.set_defaults(func=cmd_search_qa)

    # audit-log 命令
    p_audit = subparsers.add_parser("audit-log", help="查看审计日志")
    p_audit.add_argument("project_dir", nargs="?", help="项目目录")
    p_audit.add_argument("--limit", "-n", type=int, default=20, help="显示条数")
    p_audit.set_defaults(func=cmd_audit_log)

    # qa 命令 (问答记录)
    p_qa = subparsers.add_parser("qa", help="问答记录操作")
    p_qa.add_argument("project_dir", nargs="?", help="项目目录")
    p_qa.add_argument("--record", action="store_true", help="直接记录问答（推荐）")
    p_qa.add_argument("--auto", action="store_true", help="自动记录最近问答")
    p_qa.add_argument("--question", "-q", help="问题内容")
    p_qa.add_argument("--answer", "-a", help="答案内容")
    p_qa.add_argument("--files", "-f", help="相关文件（逗号分隔）")
    p_qa.add_argument("--tags", "-t", help="标签（逗号分隔）")
    p_qa.add_argument("--search", "-s", help="搜索问答")
    p_qa.add_argument("--list", "-l", action="store_true", help="列出所有问答")
    p_qa.add_argument("--check", "-c", action="store_true", help="检查过期问答")
    p_qa.add_argument("--delete", "-d", help="删除指定 ID 的问答")
    p_qa.add_argument("--category", help="分类筛选")
    p_qa.set_defaults(func=cmd_qa)

    # config 命令 (配置管理)
    p_config = subparsers.add_parser("config", help="配置管理")
    p_config.add_argument("action", choices=["get", "set", "delete", "show", "schema"], help="操作类型")
    p_config.add_argument("key", nargs="?", help="配置键")
    p_config.add_argument("value", nargs="?", help="配置值")
    p_config.set_defaults(func=cmd_config)

    # call-chain 命令 (调用链分析)
    p_call = subparsers.add_parser("call-chain", help="调用链分析")
    p_call.add_argument("project_dir", nargs="?", help="项目目录")
    p_call.add_argument("function", nargs="?", help="函数名")
    p_call.add_argument("--depth", "-d", type=int, default=3, help="分析深度")
    p_call.add_argument("--direction", choices=["calls", "called_by", "both"], default="both", help="方向")
    p_call.add_argument("--impact", action="store_true", help="影响分析")
    p_call.set_defaults(func=cmd_call_chain)

    # feishu 命令 (飞书集成)
    p_feishu = subparsers.add_parser("feishu", help="飞书文档集成")
    p_feishu.add_argument("action", choices=["report", "status", "suggest", "config"], help="操作类型")
    p_feishu.add_argument("project_dir", nargs="?", help="项目目录")
    p_feishu.add_argument("--doc-token", help="文档 Token")
    p_feishu.add_argument("--file", "-f", help="文件路径")
    p_feishu.add_argument("--type", "-t", help="变更类型")
    p_feishu.set_defaults(func=cmd_feishu)

    # cache 命令 (缓存管理)
    p_cache = subparsers.add_parser("cache", help="缓存管理")
    p_cache.add_argument("action", choices=["check", "update", "clear", "info"], help="操作类型")
    p_cache.add_argument("project_dir", nargs="?", help="项目目录")
    p_cache.add_argument("--quick", "-q", action="store_true", help="快速检查模式")
    p_cache.add_argument("--incremental", "-i", action="store_true", help="增量更新")
    p_cache.set_defaults(func=cmd_cache)

    # ============== v3.0 Commands ==============

    # index 命令 (分层索引)
    p_index = subparsers.add_parser("index", help="分层索引操作")
    p_index.add_argument("action", choices=["build", "search", "stats", "update"], help="操作类型")
    p_index.add_argument("project_dir", nargs="?", help="项目目录")
    p_index.add_argument("--level", "-l", type=int, default=0, help="索引层级 (0-2)")
    p_index.add_argument("--query", "-q", help="搜索查询")
    p_index.set_defaults(func=cmd_index)

    # multi-repo 命令 (多仓库)
    p_multi = subparsers.add_parser("multi-repo", help="多仓库操作")
    p_multi.add_argument("action", choices=["list", "detect", "search", "graph", "sync", "add"], help="操作类型")
    p_multi.add_argument("project_dir", nargs="?", help="项目目录")
    p_multi.add_argument("--query", "-q", help="搜索查询")
    p_multi.add_argument("--name", help="仓库名称")
    p_multi.add_argument("--path", help="仓库路径")
    p_multi.add_argument("--type", help="仓库类型")
    p_multi.set_defaults(func=cmd_multi_repo)

    # team 命令 (团队协作)
    p_team = subparsers.add_parser("team", help="团队协作操作")
    p_team.add_argument("action", choices=["stats", "share", "import", "search", "members"], help="操作类型")
    p_team.add_argument("project_dir", nargs="?", help="项目目录")
    p_team.add_argument("--team", "-t", help="团队名称")
    p_team.add_argument("--qa-id", help="问答 ID")
    p_team.add_argument("--author", help="作者")
    p_team.add_argument("--query", "-q", help="搜索查询")
    p_team.add_argument("--team-id", help="团队 ID")
    p_team.set_defaults(func=cmd_team)

    # ci 命令 (CI/CD 集成)
    p_ci = subparsers.add_parser("ci", help="CI/CD 集成操作")
    p_ci.add_argument("action", choices=["analyze-pr", "generate-config"], help="操作类型")
    p_ci.add_argument("project_dir", nargs="?", help="项目目录")
    p_ci.add_argument("--pr-number", type=int, help="PR 编号")
    p_ci.add_argument("--platform", choices=["github", "gitlab"], default="github", help="CI 平台")
    p_ci.set_defaults(func=cmd_ci)

    # issue 命令 (Issue 集成)
    p_issue = subparsers.add_parser("issue", help="Issue 系统集成操作")
    p_issue.add_argument("action", choices=["link", "issues", "file-issues", "sync"], help="操作类型")
    p_issue.add_argument("project_dir", nargs="?", help="项目目录")
    p_issue.add_argument("--qa-id", help="问答 ID")
    p_issue.add_argument("--issue-url", help="Issue URL")
    p_issue.add_argument("--file", help="文件路径")
    p_issue.set_defaults(func=cmd_issue)

    # ai 命令 (AI 能力)
    p_ai = subparsers.add_parser("ai", help="AI 能力操作")
    p_ai.add_argument("action", choices=["search", "build-index", "complete", "stats"], help="操作类型")
    p_ai.add_argument("project_dir", nargs="?", help="项目目录")
    p_ai.add_argument("--query", "-q", help="搜索查询")
    p_ai.add_argument("--file", "-f", help="文件路径")
    p_ai.add_argument("--line", type=int, help="行号")
    p_ai.add_argument("--prefix", help="补全前缀")
    p_ai.set_defaults(func=cmd_ai)

    # review 命令 (代码审查)
    p_review = subparsers.add_parser("review", help="代码审查和重构建议")
    p_review.add_argument("project_dir", nargs="?", help="项目目录")
    p_review.add_argument("--file", "-f", help="审查单个文件")
    p_review.set_defaults(func=cmd_review)

    # risk 命令 (风险预测)
    p_risk = subparsers.add_parser("risk", help="代码风险预测")
    p_risk.add_argument("project_dir", nargs="?", help="项目目录")
    p_risk.add_argument("--file", "-f", help="预测单个文件")
    p_risk.set_defaults(func=cmd_risk)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()