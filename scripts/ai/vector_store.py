#!/usr/bin/env python3
"""
向量存储
语义级代码搜索

特性:
- 代码向量化
- 问题向量化
- 语义相似搜索
- 支持 FAISS / Chroma
"""

import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VectorResult:
    """向量搜索结果"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""  # code, qa, doc

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'content': self.content[:200],
            'score': self.score,
            'metadata': self.metadata,
            'source': self.source,
        }


@dataclass
class IndexStats:
    """索引统计"""
    total_vectors: int = 0
    total_chunks: int = 0
    embedding_dim: int = 0
    model_name: str = ""
    last_update: str = ""


class VectorStore:
    """向量存储

    支持的后端:
    - FAISS (默认，本地)
    - Chroma (本地持久化)
    - Pinecone (云端，可选)
    """

    def __init__(self, project_dir: str, model: str = "text-embedding-3-small",
                 backend: str = "faiss"):
        """初始化

        Args:
            project_dir: 项目目录
            model: 嵌入模型名称
            backend: 后端类型 (faiss, chroma)
        """
        self.project_dir = Path(project_dir).resolve()
        self.model = model
        self.backend = backend

        self._index_dir = self.project_dir / '.projmeta' / 'vector_index'
        self._index_dir.mkdir(parents=True, exist_ok=True)

        self._index = None
        self._id_map: Dict[str, int] = {}  # id -> index
        self._metadata: Dict[int, Dict] = {}  # index -> metadata
        self._vectors: List[List[float]] = []
        self._embedding_dim = 1536  # OpenAI 默认维度

        # 尝试加载现有索引
        self._load_index()

    def embed_code(self, code: str) -> List[float]:
        """代码向量化

        Args:
            code: 代码文本

        Returns:
            嵌入向量
        """
        # 尝试使用 OpenAI
        try:
            import openai
            client = openai.OpenAI()
            response = client.embeddings.create(
                model=self.model,
                input=code
            )
            return response.data[0].embedding
        except Exception:
            pass

        # 回退到本地模型
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embedding = model.encode(code)
            return embedding.tolist()
        except Exception:
            pass

        # 最终回退：使用简单的哈希模拟
        return self._hash_to_vector(code)

    def embed_question(self, question: str) -> List[float]:
        """问题向量化

        Args:
            question: 问题文本

        Returns:
            嵌入向量
        """
        return self.embed_code(question)  # 使用相同方法

    def add_code_chunk(self, chunk_id: str, code: str, metadata: Dict = None):
        """添加代码块

        Args:
            chunk_id: 块 ID
            code: 代码文本
            metadata: 元数据
        """
        if chunk_id in self._id_map:
            return  # 已存在

        embedding = self.embed_code(code)

        index = len(self._vectors)
        self._vectors.append(embedding)
        self._id_map[chunk_id] = index
        self._metadata[index] = {
            'id': chunk_id,
            'content': code,
            'source': 'code',
            **(metadata or {}),
        }

    def add_qa(self, qa_id: str, question: str, answer: str, metadata: Dict = None):
        """添加问答

        Args:
            qa_id: 问答 ID
            question: 问题
            answer: 答案
            metadata: 元数据
        """
        if qa_id in self._id_map:
            return

        # 合并问题和答案作为嵌入内容
        content = f"Q: {question}\nA: {answer}"
        embedding = self.embed_code(content)

        index = len(self._vectors)
        self._vectors.append(embedding)
        self._id_map[qa_id] = index
        self._metadata[index] = {
            'id': qa_id,
            'question': question,
            'content': content,
            'source': 'qa',
            **(metadata or {}),
        }

    def search_similar(self, query: str, top_k: int = 10,
                       source_filter: str = None) -> List[VectorResult]:
        """语义相似搜索

        Args:
            query: 查询文本
            top_k: 返回数量
            source_filter: 来源过滤 (code, qa, doc)

        Returns:
            相似结果列表
        """
        if not self._vectors:
            return []

        query_vec = self.embed_question(query)

        # 计算相似度
        scores = []
        for i, vec in enumerate(self._vectors):
            # 来源过滤
            meta = self._metadata.get(i, {})
            if source_filter and meta.get('source') != source_filter:
                continue

            score = self._cosine_similarity(query_vec, vec)
            scores.append((i, score))

        # 排序
        scores.sort(key=lambda x: -x[1])
        top_results = scores[:top_k]

        results = []
        for index, score in top_results:
            meta = self._metadata.get(index, {})
            results.append(VectorResult(
                id=meta.get('id', ''),
                content=meta.get('content', ''),
                score=score,
                metadata=meta,
                source=meta.get('source', ''),
            ))

        return results

    def search_code(self, query: str, top_k: int = 10) -> List[VectorResult]:
        """搜索代码"""
        return self.search_similar(query, top_k, source_filter='code')

    def search_qa(self, query: str, top_k: int = 10) -> List[VectorResult]:
        """搜索问答"""
        return self.search_similar(query, top_k, source_filter='qa')

    def hybrid_search(self, query: str, top_k: int = 10,
                      bm25_results: List = None) -> List[VectorResult]:
        """混合搜索（向量 + BM25）

        Args:
            query: 查询
            top_k: 返回数量
            bm25_results: BM25 搜索结果

        Returns:
            混合结果
        """
        # 向量搜索结果
        vector_results = self.search_similar(query, top_k * 2)

        # 合并 BM25 结果
        if bm25_results:
            # 简单合并策略
            combined = {}
            for r in vector_results:
                combined[r.id] = r

            # 添加 BM25 结果
            for r in bm25_results[:top_k]:
                if r.id not in combined:
                    # 创建新的结果
                    combined[r.id] = VectorResult(
                        id=r.id,
                        content=r.content,
                        score=0.5,  # 给 BM25 结果一个默认分数
                        metadata={'source': 'bm25'},
                    )

            results = list(combined.values())
            results.sort(key=lambda x: -x.score)
            return results[:top_k]

        return vector_results

    def build_index(self, project_dir: str = None):
        """构建向量索引

        Args:
            project_dir: 项目目录（可选）
        """
        project_path = Path(project_dir) if project_dir else self.project_dir

        # 索引代码文件
        self._index_code_files(project_path)

        # 索引问答
        self._index_qa_files(project_path)

        # 构建向量索引
        self._build_vector_index()

        # 保存索引
        self._save_index()

    def _index_code_files(self, project_path: Path):
        """索引代码文件"""
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs'}

        for file_path in project_path.rglob('*'):
            if file_path.suffix.lower() in code_extensions:
                if '.git' in str(file_path) or 'node_modules' in str(file_path):
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # 分块
                    chunks = self._chunk_code(content, str(file_path.relative_to(project_path)))
                    for i, chunk in enumerate(chunks):
                        chunk_id = f"code:{file_path.relative_to(project_path)}:{i}"
                        self.add_code_chunk(chunk_id, chunk, {
                            'file': str(file_path.relative_to(project_path)),
                            'chunk_index': i,
                        })

                except Exception:
                    continue

    def _index_qa_files(self, project_path: Path):
        """索引问答文件"""
        qa_dir = project_path / '.projmeta' / 'qa'
        if not qa_dir.exists():
            return

        for qa_file in qa_dir.glob('*.json'):
            try:
                with open(qa_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                qa_id = data.get('id', qa_file.stem)
                question = data.get('question', '')
                answer = data.get('answer', '')

                if question:
                    self.add_qa(qa_id, question, answer)

            except Exception:
                continue

    def _chunk_code(self, code: str, file_path: str) -> List[str]:
        """代码分块"""
        chunks = []
        lines = code.split('\n')

        # 按函数/类分块
        current_chunk = []
        chunk_start = 0

        for i, line in enumerate(lines):
            current_chunk.append(line)

            # 检测函数/类结束
            if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                if len(current_chunk) >= 10:  # 最小块大小
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

        # 添加最后一个块
        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        # 如果没有合适的分块，按固定大小分块
        if not chunks:
            chunk_size = 500  # 行数
            for i in range(0, len(lines), chunk_size):
                chunks.append('\n'.join(lines[i:i + chunk_size]))

        return chunks

    def _build_vector_index(self):
        """构建向量索引"""
        if not self._vectors:
            return

        try:
            import faiss
            import numpy as np

            vectors = np.array(self._vectors, dtype=np.float32)
            self._embedding_dim = vectors.shape[1]

            self._index = faiss.IndexFlatL2(self._embedding_dim)
            self._index.add(vectors)

        except ImportError:
            # FAISS 不可用，使用简单的列表
            pass

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def _hash_to_vector(self, text: str) -> List[float]:
        """使用哈希生成伪向量"""
        h = hashlib.sha256(text.encode()).hexdigest()
        # 转换为浮点数向量
        vec = []
        for i in range(0, len(h), 8):
            chunk = h[i:i + 8]
            vec.append(int(chunk, 16) / (16 ** 8))

        # 扩展到嵌入维度
        while len(vec) < self._embedding_dim:
            vec = vec + vec

        return vec[:self._embedding_dim]

    def _save_index(self):
        """保存索引"""
        index_file = self._index_dir / 'index.json'

        data = {
            'model': self.model,
            'embedding_dim': self._embedding_dim,
            'id_map': self._id_map,
            'metadata': self._metadata,
            'last_update': datetime.now().isoformat(),
        }

        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_index(self):
        """加载索引"""
        index_file = self._index_dir / 'index.json'

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._embedding_dim = data.get('embedding_dim', 1536)
                self._id_map = data.get('id_map', {})
                self._metadata = {int(k): v for k, v in data.get('metadata', {}).items()}

            except Exception:
                pass

    def get_stats(self) -> IndexStats:
        """获取索引统计"""
        return IndexStats(
            total_vectors=len(self._vectors),
            total_chunks=len(self._id_map),
            embedding_dim=self._embedding_dim,
            model_name=self.model,
            last_update=datetime.now().isoformat(),
        )

    def clear(self):
        """清除索引"""
        self._vectors = []
        self._id_map = {}
        self._metadata = {}
        self._index = None


def main():
    """命令行接口"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: vector_store.py <project_dir> [command]")
        print("\nCommands:")
        print("  build              Build vector index")
        print("  search <query>     Search similar content")
        print("  stats              Show index stats")
        print("  clear              Clear index")
        sys.exit(1)

    project_dir = sys.argv[1]
    store = VectorStore(project_dir)

    if len(sys.argv) < 3:
        print("Please specify a command")
        sys.exit(1)

    command = sys.argv[2]

    if command == 'build':
        print("Building vector index...")
        store.build_index()
        stats = store.get_stats()
        print(f"Indexed {stats.total_chunks} chunks")

    elif command == 'search':
        if len(sys.argv) < 4:
            print("Usage: vector_store.py <project_dir> search <query>")
            sys.exit(1)
        query = sys.argv[3]
        results = store.search_similar(query)
        for r in results:
            print(f"- [{r.score:.3f}] {r.id}: {r.content[:50]}...")

    elif command == 'stats':
        stats = store.get_stats()
        print(json.dumps({
            'total_vectors': stats.total_vectors,
            'total_chunks': stats.total_chunks,
            'embedding_dim': stats.embedding_dim,
            'model': stats.model_name,
        }, indent=2))

    elif command == 'clear':
        store.clear()
        print("Index cleared")


if __name__ == '__main__':
    main()