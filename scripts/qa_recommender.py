#!/usr/bin/env python3
"""
智能问答推荐器
基于上下文和历史记录推荐相关问答

特性：
- 基于当前文件上下文推荐
- 基于用户历史推荐
- 基于代码结构推荐
- 热门问题推荐
"""

import os
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import Counter, defaultdict


@dataclass
class Recommendation:
    """推荐结果"""
    qa_id: str
    question: str
    relevance_score: float
    reason: str
    source: str  # context, history, structure, popular


@dataclass
class UserHistory:
    """用户历史"""
    user_id: str
    queries: List[Dict[str, Any]] = field(default_factory=list)
    accessed_qa: List[str] = field(default_factory=list)
    file_views: List[str] = field(default_factory=list)


class QARecommender:
    """智能问答推荐器"""

    HISTORY_FILE = '.projmeta/qa_history.json'
    MAX_HISTORY = 100

    def __init__(self, project_dir: str):
        """初始化推荐器

        Args:
            project_dir: 项目目录
        """
        self.project_dir = Path(project_dir).resolve()
        self._history_path = self.project_dir / self.HISTORY_FILE

        # 用户历史
        self._user_histories: Dict[str, UserHistory] = {}

        # 全局统计
        self._qa_access_count: Counter = Counter()
        self._qa_by_intent: Dict[str, List[str]] = defaultdict(list)
        self._file_to_qa: Dict[str, List[str]] = defaultdict(list)

        # 热门缓存
        self._popular_qa: List[Tuple[str, int]] = []
        self._popular_update_time: datetime = None

        self._load()

    def _load(self) -> None:
        """加载历史数据"""
        if not self._history_path.exists():
            return

        try:
            with open(self._history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 加载用户历史
            for user_id, history_data in data.get('user_histories', {}).items():
                self._user_histories[user_id] = UserHistory(
                    user_id=user_id,
                    queries=history_data.get('queries', []),
                    accessed_qa=history_data.get('accessed_qa', []),
                    file_views=history_data.get('file_views', []),
                )

            # 加载全局统计
            self._qa_access_count = Counter(data.get('qa_access_count', {}))

            # 加载文件关联
            for file, qa_ids in data.get('file_to_qa', {}).items():
                self._file_to_qa[file] = qa_ids

        except Exception:
            pass

    def _save(self) -> None:
        """保存历史数据"""
        self._history_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'user_histories': {},
            'qa_access_count': dict(self._qa_access_count),
            'file_to_qa': dict(self._file_to_qa),
        }

        for user_id, history in self._user_histories.items():
            data['user_histories'][user_id] = {
                'queries': history.queries[-self.MAX_HISTORY:],
                'accessed_qa': history.accessed_qa[-self.MAX_HISTORY:],
                'file_views': history.file_views[-self.MAX_HISTORY:],
            }

        try:
            with open(self._history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def record_access(self, qa_id: str, user_id: str = "default",
                      file_context: str = None) -> None:
        """记录问答访问

        Args:
            qa_id: 问答ID
            user_id: 用户ID
            file_context: 当前文件上下文
        """
        # 更新用户历史
        if user_id not in self._user_histories:
            self._user_histories[user_id] = UserHistory(user_id=user_id)

        history = self._user_histories[user_id]
        history.accessed_qa.append(qa_id)

        if file_context:
            history.file_views.append(file_context)
            # 建立文件-问答关联
            if qa_id not in self._file_to_qa[file_context]:
                self._file_to_qa[file_context].append(qa_id)

        # 更新全局统计
        self._qa_access_count[qa_id] += 1

        self._save()

    def record_query(self, query: str, user_id: str = "default",
                     matched_qa: str = None) -> None:
        """记录查询

        Args:
            query: 查询内容
            user_id: 用户ID
            matched_qa: 匹配的问答ID
        """
        if user_id not in self._user_histories:
            self._user_histories[user_id] = UserHistory(user_id=user_id)

        history = self._user_histories[user_id]
        history.queries.append({
            'query': query,
            'qa_id': matched_qa,
            'timestamp': datetime.now().isoformat(),
        })

        self._save()

    def recommend_by_context(self, current_file: str,
                              top_k: int = 5) -> List[Recommendation]:
        """基于当前上下文推荐相关问答

        Args:
            current_file: 当前文件
            top_k: 推荐数量

        Returns:
            推荐列表
        """
        recommendations = []

        # 1. 直接关联的问答
        if current_file in self._file_to_qa:
            for qa_id in self._file_to_qa[current_file][:top_k]:
                count = self._qa_access_count.get(qa_id, 0)
                score = 0.8 + min(count * 0.02, 0.2)  # 访问次数加分
                recommendations.append(Recommendation(
                    qa_id=qa_id,
                    question="",  # 需要从QA缓存获取
                    relevance_score=score,
                    reason=f"与当前文件 {current_file} 相关",
                    source="context",
                ))

        # 2. 基于文件路径模式推荐
        file_stem = Path(current_file).stem
        file_ext = Path(current_file).suffix

        # 查找相似文件关联的问答
        for file_path, qa_ids in self._file_to_qa.items():
            if file_path == current_file:
                continue

            # 相同目录或相似文件名
            if file_stem in file_path or Path(file_path).stem in current_file:
                for qa_id in qa_ids[:2]:
                    if not any(r.qa_id == qa_id for r in recommendations):
                        recommendations.append(Recommendation(
                            qa_id=qa_id,
                            question="",
                            relevance_score=0.6,
                            reason=f"与相似文件 {file_path} 相关",
                            source="context",
                        ))

        return recommendations[:top_k]

    def recommend_by_history(self, user_id: str = "default",
                              top_k: int = 5) -> List[Recommendation]:
        """基于用户历史推荐

        Args:
            user_id: 用户ID
            top_k: 推荐数量

        Returns:
            推荐列表
        """
        recommendations = []

        if user_id not in self._user_histories:
            return recommendations

        history = self._user_histories[user_id]

        # 分析访问模式
        qa_frequency = Counter(history.accessed_qa)

        # 最近访问的问答（高频）
        recent_qa = qa_frequency.most_common(top_k * 2)

        for qa_id, count in recent_qa[:top_k]:
            if count >= 2:  # 至少访问过2次
                recommendations.append(Recommendation(
                    qa_id=qa_id,
                    question="",
                    relevance_score=0.7 + min(count * 0.05, 0.3),
                    reason=f"您之前访问过 {count} 次",
                    source="history",
                ))

        return recommendations[:top_k]

    def recommend_by_popular(self, top_k: int = 5,
                              min_access: int = 3) -> List[Recommendation]:
        """推荐热门问题

        Args:
            top_k: 推荐数量
            min_access: 最小访问次数

        Returns:
            推荐列表
        """
        recommendations = []

        # 获取热门问答
        popular = self._qa_access_count.most_common(top_k * 2)

        for qa_id, count in popular[:top_k]:
            if count >= min_access:
                recommendations.append(Recommendation(
                    qa_id=qa_id,
                    question="",
                    relevance_score=0.5 + min(count * 0.03, 0.5),
                    reason=f"被访问 {count} 次的热门问题",
                    source="popular",
                ))

        return recommendations[:top_k]

    def recommend_by_structure(self, file_path: str,
                                imports: List[str] = None,
                                functions: List[str] = None,
                                top_k: int = 5) -> List[Recommendation]:
        """基于代码结构推荐

        Args:
            file_path: 文件路径
            imports: 导入列表
            functions: 函数列表
            top_k: 推荐数量

        Returns:
            推荐列表
        """
        recommendations = []

        # 基于导入推荐
        if imports:
            for imp in imports[:5]:
                # 查找与导入相关的问答
                for f, qa_ids in self._file_to_qa.items():
                    if imp in f:
                        for qa_id in qa_ids[:1]:
                            if not any(r.qa_id == qa_id for r in recommendations):
                                recommendations.append(Recommendation(
                                    qa_id=qa_id,
                                    question="",
                                    relevance_score=0.5,
                                    reason=f"与导入 {imp} 相关",
                                    source="structure",
                                ))

        # 基于函数推荐
        if functions:
            for func in functions[:5]:
                for f, qa_ids in self._file_to_qa.items():
                    if func in f:
                        for qa_id in qa_ids[:1]:
                            if not any(r.qa_id == qa_id for r in recommendations):
                                recommendations.append(Recommendation(
                                    qa_id=qa_id,
                                    question="",
                                    relevance_score=0.5,
                                    reason=f"与函数 {func} 相关",
                                    source="structure",
                                ))

        return recommendations[:top_k]

    def get_recommendations(self, current_file: str = None,
                            user_id: str = "default",
                            top_k: int = 10) -> List[Recommendation]:
        """获取综合推荐

        Args:
            current_file: 当前文件
            user_id: 用户ID
            top_k: 推荐数量

        Returns:
            推荐列表
        """
        all_recommendations = []

        # 上下文推荐
        if current_file:
            all_recommendations.extend(
                self.recommend_by_context(current_file, top_k // 2)
            )

        # 历史推荐
        all_recommendations.extend(
            self.recommend_by_history(user_id, top_k // 3)
        )

        # 热门推荐
        all_recommendations.extend(
            self.recommend_by_popular(top_k // 3)
        )

        # 去重并排序
        seen = set()
        unique_recommendations = []
        for r in all_recommendations:
            if r.qa_id not in seen:
                seen.add(r.qa_id)
                unique_recommendations.append(r)

        unique_recommendations.sort(key=lambda x: x.relevance_score, reverse=True)

        return unique_recommendations[:top_k]

    def get_similar_queries(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """获取相似查询

        Args:
            query: 当前查询
            top_k: 返回数量

        Returns:
            相似查询列表
        """
        similar = []

        # 从所有用户历史中查找相似查询
        for user_id, history in self._user_histories.items():
            for q in history.queries:
                stored_query = q.get('query', '')
                if stored_query and self._is_similar(query, stored_query):
                    similar.append({
                        'query': stored_query,
                        'qa_id': q.get('qa_id'),
                        'timestamp': q.get('timestamp'),
                    })

        # 按时间排序
        similar.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return similar[:top_k]

    def _is_similar(self, q1: str, q2: str) -> bool:
        """判断两个查询是否相似"""
        # 简单的关键词重叠判断
        words1 = set(q1.lower().split())
        words2 = set(q2.lower().split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) > 0.5

    def get_statistics(self) -> Dict[str, Any]:
        """获取推荐器统计"""
        return {
            'total_users': len(self._user_histories),
            'total_qa_accessed': sum(self._qa_access_count.values()),
            'unique_qa_accessed': len(self._qa_access_count),
            'files_with_qa': len(self._file_to_qa),
            'top_accessed_qa': self._qa_access_count.most_common(10),
        }

    def clear_history(self, user_id: str = None) -> None:
        """清空历史

        Args:
            user_id: 用户ID（None = 清空所有）
        """
        if user_id:
            if user_id in self._user_histories:
                del self._user_histories[user_id]
        else:
            self._user_histories.clear()
            self._qa_access_count.clear()
            self._file_to_qa.clear()

        self._save()


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: qa_recommender.py <project_dir> [command]")
        print("\nCommands:")
        print("  recommend [file]       Get recommendations")
        print("  popular                Get popular QA")
        print("  stats                  Show statistics")
        print("  history <user_id>      Show user history")
        sys.exit(1)

    project_dir = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'recommend'

    recommender = QARecommender(project_dir)

    if command == 'recommend':
        current_file = sys.argv[3] if len(sys.argv) > 3 else None
        recommendations = recommender.get_recommendations(current_file)

        print("推荐问答:")
        for i, r in enumerate(recommendations, 1):
            print(f"{i}. [{r.source}] {r.qa_id[:8]}... (score: {r.relevance_score:.2f})")
            print(f"   原因: {r.reason}")

    elif command == 'popular':
        popular = recommender.recommend_by_popular()
        print("热门问答:")
        for i, r in enumerate(popular, 1):
            print(f"{i}. {r.qa_id[:8]}... - {r.reason}")

    elif command == 'stats':
        stats = recommender.get_statistics()
        print(json.dumps(stats, indent=2, ensure_ascii=False))

    elif command == 'history':
        user_id = sys.argv[3] if len(sys.argv) > 3 else 'default'
        if user_id in recommender._user_histories:
            history = recommender._user_histories[user_id]
            print(f"用户 {user_id} 历史:")
            print(f"  查询数: {len(history.queries)}")
            print(f"  访问问答: {len(history.accessed_qa)}")
            print(f"  浏览文件: {len(history.file_views)}")
        else:
            print(f"用户 {user_id} 无历史记录")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()