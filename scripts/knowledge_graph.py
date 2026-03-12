#!/usr/bin/env python3
"""
问答知识图谱
关联问答与代码、测试、文档等，支持关联查询和过期检测

特性：
- 问答与代码文件关联
- 问答与测试用例关联
- 代码变更影响分析
- 过期问答检测
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


@dataclass
class QANode:
    """问答节点"""
    qa_id: str
    question: str
    normalized_question: str
    intent: str
    created_at: str
    last_accessed: str
    access_count: int = 0
    confidence: float = 1.0


@dataclass
class CodeRef:
    """代码引用"""
    file_path: str
    line_start: int = 0
    line_end: int = 0
    symbol: str = ""  # 函数名、类名等
    relevance: float = 1.0  # 相关度


@dataclass
class TestRef:
    """测试引用"""
    test_file: str
    test_name: str
    test_type: str = "unit"  # unit, integration, e2e


@dataclass
class DocRef:
    """文档引用"""
    doc_file: str
    section: str = ""
    doc_type: str = "markdown"  # markdown, rst, etc.


class KnowledgeGraph:
    """问答知识图谱"""

    GRAPH_FILE = '.projmeta/knowledge_graph.json'

    def __init__(self, project_dir: str):
        """初始化知识图谱

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self._graph_path = self.project_dir / self.GRAPH_FILE
        self._dirty = False

        # 存储结构
        self._qa_nodes: Dict[str, QANode] = {}
        self._code_refs: Dict[str, List[CodeRef]] = defaultdict(list)
        self._test_refs: Dict[str, List[TestRef]] = defaultdict(list)
        self._doc_refs: Dict[str, List[DocRef]] = defaultdict(list)

        # 反向索引
        self._file_to_qa: Dict[str, Set[str]] = defaultdict(set)
        self._symbol_to_qa: Dict[str, Set[str]] = defaultdict(set)

        # 文件修改时间记录
        self._file_mtimes: Dict[str, float] = {}

        self._load()

    def _load(self) -> None:
        """加载图谱"""
        if not self._graph_path.exists():
            return

        try:
            with open(self._graph_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载问答节点
            for qa_id, node_data in data.get('qa_nodes', {}).items():
                self._qa_nodes[qa_id] = QANode(
                    qa_id=qa_id,
                    question=node_data.get('question', ''),
                    normalized_question=node_data.get('normalized_question', ''),
                    intent=node_data.get('intent', ''),
                    created_at=node_data.get('created_at', ''),
                    last_accessed=node_data.get('last_accessed', ''),
                    access_count=node_data.get('access_count', 0),
                    confidence=node_data.get('confidence', 1.0),
                )

            # 加载代码引用
            for qa_id, refs in data.get('code_refs', {}).items():
                for ref in refs:
                    self._code_refs[qa_id].append(CodeRef(
                        file_path=ref.get('file_path', ''),
                        line_start=ref.get('line_start', 0),
                        line_end=ref.get('line_end', 0),
                        symbol=ref.get('symbol', ''),
                        relevance=ref.get('relevance', 1.0),
                    ))
                    # 建立反向索引
                    self._file_to_qa[ref.get('file_path', '')].add(qa_id)
                    if ref.get('symbol'):
                        self._symbol_to_qa[ref.get('symbol', '')].add(qa_id)

            # 加载测试引用
            for qa_id, refs in data.get('test_refs', {}).items():
                for ref in refs:
                    self._test_refs[qa_id].append(TestRef(
                        test_file=ref.get('test_file', ''),
                        test_name=ref.get('test_name', ''),
                        test_type=ref.get('test_type', 'unit'),
                    ))

            # 加载文档引用
            for qa_id, refs in data.get('doc_refs', {}).items():
                for ref in refs:
                    self._doc_refs[qa_id].append(DocRef(
                        doc_file=ref.get('doc_file', ''),
                        section=ref.get('section', ''),
                        doc_type=ref.get('doc_type', 'markdown'),
                    ))

            # 加载文件修改时间
            self._file_mtimes = data.get('file_mtimes', {})

        except Exception as e:
            print(f"Warning: Failed to load knowledge graph: {e}")

    def _save(self) -> None:
        """保存图谱"""
        if not self._dirty:
            return

        self._graph_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'qa_nodes': {},
            'code_refs': {},
            'test_refs': {},
            'doc_refs': {},
            'file_mtimes': self._file_mtimes,
        }

        # 序列化问答节点
        for qa_id, node in self._qa_nodes.items():
            data['qa_nodes'][qa_id] = {
                'question': node.question,
                'normalized_question': node.normalized_question,
                'intent': node.intent,
                'created_at': node.created_at,
                'last_accessed': node.last_accessed,
                'access_count': node.access_count,
                'confidence': node.confidence,
            }

        # 序列化代码引用
        for qa_id, refs in self._code_refs.items():
            data['code_refs'][qa_id] = [
                {
                    'file_path': r.file_path,
                    'line_start': r.line_start,
                    'line_end': r.line_end,
                    'symbol': r.symbol,
                    'relevance': r.relevance,
                }
                for r in refs
            ]

        # 序列化测试引用
        for qa_id, refs in self._test_refs.items():
            data['test_refs'][qa_id] = [
                {
                    'test_file': r.test_file,
                    'test_name': r.test_name,
                    'test_type': r.test_type,
                }
                for r in refs
            ]

        # 序列化文档引用
        for qa_id, refs in self._doc_refs.items():
            data['doc_refs'][qa_id] = [
                {
                    'doc_file': r.doc_file,
                    'section': r.section,
                    'doc_type': r.doc_type,
                }
                for r in refs
            ]

        try:
            with open(self._graph_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._dirty = False
        except Exception as e:
            print(f"Warning: Failed to save knowledge graph: {e}")

    def add_qa(self, qa_id: str, question: str, intent: str = "") -> None:
        """添加问答节点

        Args:
            qa_id: 问答ID
            question: 问题
            intent: 意图
        """
        now = datetime.now().isoformat()
        self._qa_nodes[qa_id] = QANode(
            qa_id=qa_id,
            question=question,
            normalized_question=self._normalize_question(question),
            intent=intent,
            created_at=now,
            last_accessed=now,
        )
        self._dirty = True

    def _normalize_question(self, question: str) -> str:
        """规范化问题"""
        import re
        q = question.strip().lower()
        q = re.sub(r'\s+', ' ', q)
        return q

    def link_qa_to_code(self, qa_id: str, code_refs: List[Dict[str, Any]]) -> None:
        """关联问答与代码

        Args:
            qa_id: 问答ID
            code_refs: 代码引用列表
        """
        for ref in code_refs:
            code_ref = CodeRef(
                file_path=ref.get('file_path', ''),
                line_start=ref.get('line_start', 0),
                line_end=ref.get('line_end', 0),
                symbol=ref.get('symbol', ''),
                relevance=ref.get('relevance', 1.0),
            )
            self._code_refs[qa_id].append(code_ref)

            # 建立反向索引
            self._file_to_qa[code_ref.file_path].add(qa_id)
            if code_ref.symbol:
                self._symbol_to_qa[code_ref.symbol].add(qa_id)

            # 记录文件修改时间
            file_path = self.project_dir / code_ref.file_path
            if file_path.exists():
                self._file_mtimes[code_ref.file_path] = file_path.stat().st_mtime

        self._dirty = True
        self._save()

    def link_qa_to_test(self, qa_id: str, test_refs: List[Dict[str, Any]]) -> None:
        """关联问答与测试

        Args:
            qa_id: 问答ID
            test_refs: 测试引用列表
        """
        for ref in test_refs:
            test_ref = TestRef(
                test_file=ref.get('test_file', ''),
                test_name=ref.get('test_name', ''),
                test_type=ref.get('test_type', 'unit'),
            )
            self._test_refs[qa_id].append(test_ref)
            self._file_to_qa[test_ref.test_file].add(qa_id)

        self._dirty = True
        self._save()

    def link_qa_to_doc(self, qa_id: str, doc_refs: List[Dict[str, Any]]) -> None:
        """关联问答与文档

        Args:
            qa_id: 问答ID
            doc_refs: 文档引用列表
        """
        for ref in doc_refs:
            doc_ref = DocRef(
                doc_file=ref.get('doc_file', ''),
                section=ref.get('section', ''),
                doc_type=ref.get('doc_type', 'markdown'),
            )
            self._doc_refs[qa_id].append(doc_ref)
            self._file_to_qa[doc_ref.doc_file].add(qa_id)

        self._dirty = True
        self._save()

    def get_related_qa(self, file: str) -> List[str]:
        """获取文件相关的问答

        Args:
            file: 文件路径

        Returns:
            相关问答ID列表
        """
        return list(self._file_to_qa.get(file, set()))

    def get_qa_code_refs(self, qa_id: str) -> List[CodeRef]:
        """获取问答的代码引用

        Args:
            qa_id: 问答ID

        Returns:
            代码引用列表
        """
        return self._code_refs.get(qa_id, [])

    def get_qa_test_refs(self, qa_id: str) -> List[TestRef]:
        """获取问答的测试引用

        Args:
            qa_id: 问答ID

        Returns:
            测试引用列表
        """
        return self._test_refs.get(qa_id, [])

    def check_qa_outdated(self, qa_id: str) -> Dict[str, Any]:
        """检查问答是否过期（基于代码变更）

        Args:
            qa_id: 问答ID

        Returns:
            过期检查结果
        """
        result = {
            'qa_id': qa_id,
            'is_outdated': False,
            'changed_files': [],
            'last_checked': datetime.now().isoformat(),
        }

        code_refs = self._code_refs.get(qa_id, [])
        for ref in code_refs:
            file_path = self.project_dir / ref.file_path

            if not file_path.exists():
                # 文件被删除
                result['is_outdated'] = True
                result['changed_files'].append({
                    'file': ref.file_path,
                    'change': 'deleted',
                })
                continue

            # 检查修改时间
            current_mtime = file_path.stat().st_mtime
            stored_mtime = self._file_mtimes.get(ref.file_path, 0)

            if current_mtime > stored_mtime:
                result['is_outdated'] = True
                result['changed_files'].append({
                    'file': ref.file_path,
                    'change': 'modified',
                })

        return result

    def update_file_mtimes(self, files: List[str] = None) -> None:
        """更新文件修改时间

        Args:
            files: 文件列表（None = 更新所有）
        """
        if files is None:
            files = list(self._file_mtimes.keys())

        for file_path in files:
            full_path = self.project_dir / file_path
            if full_path.exists():
                self._file_mtimes[file_path] = full_path.stat().st_mtime

        self._dirty = True
        self._save()

    def get_impact_analysis(self, changed_files: List[str]) -> Dict[str, Any]:
        """影响分析：哪些问答受文件变更影响

        Args:
            changed_files: 变更文件列表

        Returns:
            影响分析结果
        """
        affected_qa = set()

        for file in changed_files:
            # 直接引用的问答
            if file in self._file_to_qa:
                affected_qa.update(self._file_to_qa[file])

        # 根据符号查找关联
        for file in changed_files:
            # 简单的符号提取（从文件名）
            symbol = Path(file).stem
            if symbol in self._symbol_to_qa:
                affected_qa.update(self._symbol_to_qa[symbol])

        return {
            'changed_files': changed_files,
            'affected_qa_count': len(affected_qa),
            'affected_qa': list(affected_qa),
            'recommendations': self._generate_recommendations(affected_qa),
        }

    def _generate_recommendations(self, affected_qa: Set[str]) -> List[str]:
        """生成更新建议"""
        recommendations = []

        for qa_id in affected_qa:
            if qa_id in self._qa_nodes:
                node = self._qa_nodes[qa_id]
                recommendations.append(
                    f"问答 [{qa_id[:8]}] \"{node.question[:30]}...\" 可能需要更新"
                )

        return recommendations[:10]  # 限制数量

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计"""
        total_refs = sum(len(refs) for refs in self._code_refs.values())

        files_covered = len(self._file_to_qa)
        symbols_covered = len(self._symbol_to_qa)

        return {
            'total_qa': len(self._qa_nodes),
            'total_code_refs': total_refs,
            'total_test_refs': sum(len(refs) for refs in self._test_refs.values()),
            'total_doc_refs': sum(len(refs) for refs in self._doc_refs.values()),
            'files_covered': files_covered,
            'symbols_covered': symbols_covered,
            'graph_file': str(self._graph_path),
        }

    def remove_qa(self, qa_id: str) -> None:
        """删除问答及其关联

        Args:
            qa_id: 问答ID
        """
        # 删除节点
        if qa_id in self._qa_nodes:
            del self._qa_nodes[qa_id]

        # 删除代码引用
        if qa_id in self._code_refs:
            for ref in self._code_refs[qa_id]:
                self._file_to_qa[ref.file_path].discard(qa_id)
                if ref.symbol:
                    self._symbol_to_qa[ref.symbol].discard(qa_id)
            del self._code_refs[qa_id]

        # 删除测试引用
        if qa_id in self._test_refs:
            for ref in self._test_refs[qa_id]:
                self._file_to_qa[ref.test_file].discard(qa_id)
            del self._test_refs[qa_id]

        # 删除文档引用
        if qa_id in self._doc_refs:
            for ref in self._doc_refs[qa_id]:
                self._file_to_qa[ref.doc_file].discard(qa_id)
            del self._doc_refs[qa_id]

        self._dirty = True
        self._save()

    def clear(self) -> None:
        """清空图谱"""
        self._qa_nodes.clear()
        self._code_refs.clear()
        self._test_refs.clear()
        self._doc_refs.clear()
        self._file_to_qa.clear()
        self._symbol_to_qa.clear()
        self._file_mtimes.clear()
        self._dirty = True
        self._save()


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: knowledge_graph.py <project_dir> [command]")
        print("\nCommands:")
        print("  stats              Show graph statistics")
        print("  check <qa_id>      Check if QA is outdated")
        print("  impact <file>      Analyze impact of file change")
        print("  related <file>     Get QA related to file")
        sys.exit(1)

    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'stats'

    graph = KnowledgeGraph(project_dir)

    if command == 'stats':
        stats = graph.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif command == 'check':
        if len(sys.argv) < 4:
            print("Usage: knowledge_graph.py <project_dir> check <qa_id>")
            sys.exit(1)
        qa_id = sys.argv[3]
        result = graph.check_qa_outdated(qa_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'impact':
        if len(sys.argv) < 4:
            print("Usage: knowledge_graph.py <project_dir> impact <file>")
            sys.exit(1)
        files = sys.argv[3:]
        result = graph.get_impact_analysis(files)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == 'related':
        if len(sys.argv) < 4:
            print("Usage: knowledge_graph.py <project_dir> related <file>")
            sys.exit(1)
        file = sys.argv[3]
        qa_ids = graph.get_related_qa(file)
        print(json.dumps({'file': file, 'related_qa': qa_ids}, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()