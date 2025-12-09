"""
Schema Manager for NL2SQL system.
M3: 生成、加载和检索数据库 Schema 信息。

功能：
- 生成 schema.json（持久化）
- 智能表匹配（根据问题筛选相关表）
- 字段检索（精确/模糊/别名匹配）
- 格式化 Schema 供 Prompt 使用
"""
import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from difflib import SequenceMatcher
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.db import db_client


class SchemaManager:
    """
    Schema 管理器
    - 生成 schema.json
    - 加载和缓存 schema
    - 字段检索匹配
    - 生成表清单提示
    """
    
    def __init__(self, schema_path: Optional[str] = None):
        self.schema_path = Path(schema_path) if schema_path else project_root / "data" / "schema.json"
        self._schema_cache: Optional[Dict] = None
        self._field_index: Dict[str, List[Dict]] = {}  # 字段名 -> [{table, column}]
        
    def generate_schema_json(self, include_sample_values: bool = True, sample_limit: int = 3) -> Dict:
        """
        从数据库生成完整的 schema.json
        
        Args:
            include_sample_values: 是否包含示例值
            sample_limit: 每个字段的示例值数量
            
        Returns:
            完整的 schema 字典
        """
        tables = db_client.get_table_names()
        
        schema = {
            "database_type": "mysql",
            "generated_at": datetime.now().isoformat(),
            "tables": [],
            "table_list": tables,  # 表清单
            "field_index": {}  # 字段索引：字段名 -> 所属表列表
        }
        
        field_index = {}
        
        for table_name in tables:
            table_schema = db_client.get_table_schema(table_name)
            
            # 获取外键信息
            foreign_keys = self._get_foreign_keys(table_name)
            
            # 获取示例值
            sample_values = {}
            if include_sample_values:
                sample_values = self._get_sample_values(table_name, table_schema["columns"], sample_limit)
            
            table_info = {
                "name": table_name,
                "description": "",  # 可手动补充表描述
                "columns": [],
                "foreign_keys": foreign_keys,
                "row_count": self._get_row_count(table_name)
            }
            
            for col in table_schema["columns"]:
                col_name = col["name"]
                col_info = {
                    "name": col_name,
                    "type": col["type"],
                    "primary_key": col["primary_key"],
                    "not_null": col["not_null"],
                    "description": "",  # 可手动补充列描述
                    "aliases": self._generate_aliases(col_name),  # 字段别名（用于模糊匹配）
                    "sample_values": sample_values.get(col_name, [])
                }
                table_info["columns"].append(col_info)
                
                # 构建字段索引
                col_name_lower = col_name.lower()
                if col_name_lower not in field_index:
                    field_index[col_name_lower] = []
                field_index[col_name_lower].append({
                    "table": table_name,
                    "column": col_name,
                    "type": col["type"]
                })
            
            schema["tables"].append(table_info)
        
        schema["field_index"] = field_index
        
        # 保存到文件
        self.schema_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.schema_path, "w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
        
        print(f"✓ Schema saved to {self.schema_path}")
        self._schema_cache = schema
        self._field_index = field_index
        
        return schema
    
    def _get_foreign_keys(self, table_name: str) -> List[Dict]:
        """
        获取表的外键信息 (MySQL)
        M8: 如果数据库没有定义外键约束，则基于字段名模式推断外键关系
        """
        foreign_keys = []
        
        # 方法1: 从数据库INFORMATION_SCHEMA获取（如果存在外键约束）
        try:
            conn = db_client._get_connection()
            cursor = conn.cursor()
            
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = '{db_client.mysql_config["database"]}'
                AND TABLE_NAME = '{table_name}'
                AND REFERENCED_TABLE_NAME IS NOT NULL
            """)
            for row in cursor.fetchall():
                foreign_keys.append({
                    "column": row["COLUMN_NAME"],
                    "references_table": row["REFERENCED_TABLE_NAME"],
                    "references_column": row["REFERENCED_COLUMN_NAME"]
                })
            
            cursor.close()
            conn.close()
        except Exception as e:
            pass  # 如果查询失败，继续使用推断方法
        
        # 方法2: 如果数据库没有外键约束，基于字段名模式推断（M8）
        if not foreign_keys:
            foreign_keys = self._infer_foreign_keys(table_name)
        
        return foreign_keys
    
    def _infer_foreign_keys(self, table_name: str) -> List[Dict]:
        """
        基于字段名模式推断外键关系（M8）
        
        规则：
        1. 如果字段名以"Id"结尾（如CustomerId），且存在对应的表（如customer），则推断为外键
        2. 匹配目标表的主键（通常是表名+Id格式，如CustomerId）
        """
        foreign_keys = []
        schema = self.load_schema()
        
        # 获取当前表的字段
        current_table = None
        for table in schema["tables"]:
            if table["name"].lower() == table_name.lower():
                current_table = table
                break
        
        if not current_table:
            return foreign_keys
        
        # 获取所有表名（用于匹配）
        all_table_names = {t["name"].lower(): t["name"] for t in schema["tables"]}
        
        # 检查每个字段
        for col in current_table["columns"]:
            col_name = col["name"]
            
            # 跳过主键
            if col.get("primary_key"):
                continue
            
            # 规则: 字段名以"Id"结尾（如CustomerId, ArtistId, AlbumId, SupportRepId）
            if col_name.endswith("Id") and len(col_name) > 2:
                # 提取潜在的表名（去掉Id后缀）
                potential_table_base = col_name[:-2]  # 去掉"Id"
                
                # 特殊处理：SupportRepId -> employee, ReportsTo -> employee等
                special_mappings = {
                    "supportrep": "employee",  # SupportRepId -> employee
                    "reportsto": "employee",   # ReportsTo -> employee (如果存在)
                }
                
                # 检查特殊映射
                if potential_table_base.lower() in special_mappings:
                    potential_table_base = special_mappings[potential_table_base.lower()]
                
                # 尝试匹配表名（支持多种变体）
                matched_table = None
                matched_pk = None
                
                for table_lower, table_orig in all_table_names.items():
                    # 查找目标表
                    target_table = None
                    for t in schema["tables"]:
                        if t["name"] == table_orig:
                            target_table = t
                            break
                    
                    if not target_table:
                        continue
                    
                    # 查找主键
                    pk_column = None
                    for pk_col in target_table["columns"]:
                        if pk_col.get("primary_key"):
                            pk_column = pk_col["name"]
                            break
                    
                    if not pk_column:
                        continue
                    
                    # 匹配规则1: 精确匹配（CustomerId -> customer表）
                    if table_lower == potential_table_base.lower():
                        matched_table = table_orig
                        matched_pk = pk_column
                        break
                    
                    # 匹配规则2: 单复数匹配（customers -> customer, CustomerId）
                    table_singular = table_lower.rstrip('s')
                    if table_singular == potential_table_base.lower():
                        matched_table = table_orig
                        matched_pk = pk_column
                        break
                    
                    # 匹配规则3: 包含匹配（SupportRepId中的"Rep"可能匹配employee）
                    if "rep" in potential_table_base.lower() and "employee" in table_lower:
                        matched_table = table_orig
                        matched_pk = pk_column
                        break
                    
                    # 匹配规则4: 主键名匹配（如果主键名与字段名相同或相似）
                    if pk_column.lower() == col_name.lower():
                        matched_table = table_orig
                        matched_pk = pk_column
                        break
                
                if matched_table and matched_pk:
                    foreign_keys.append({
                        "column": col_name,
                        "references_table": matched_table,
                        "references_column": matched_pk
                    })
        
        return foreign_keys
    
    def _get_row_count(self, table_name: str) -> int:
        """获取表行数 (MySQL)"""
        result = db_client.query(f"SELECT COUNT(*) as cnt FROM `{table_name}`")
        if result["ok"] and result["rows"]:
            return result["rows"][0]["cnt"]
        return 0
    
    def _get_sample_values(self, table_name: str, columns: List[Dict], limit: int) -> Dict[str, List]:
        """获取每个字段的示例值 (MySQL)"""
        sample_values = {}
        for col in columns:
            col_name = col["name"]
            try:
                result = db_client.query(
                    f"SELECT DISTINCT `{col_name}` FROM `{table_name}` WHERE `{col_name}` IS NOT NULL LIMIT {limit}"
                )
                if result["ok"]:
                    values = [row[col_name] for row in result["rows"]]
                    # 转换为可 JSON 序列化的格式
                    sample_values[col_name] = [
                        str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v 
                        for v in values
                    ]
            except Exception:
                sample_values[col_name] = []
        return sample_values
    
    def _generate_aliases(self, column_name: str) -> List[str]:
        """
        生成字段别名（用于模糊匹配）
        例如: CustomerId -> ["customer_id", "客户id", "customerid"]
        """
        aliases = []
        
        # 转小写
        aliases.append(column_name.lower())
        
        # 驼峰转下划线
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', column_name).lower()
        if snake_case != column_name.lower():
            aliases.append(snake_case)
        
        # 常见中文映射
        chinese_mappings = {
            "customer": "客户", "id": "编号", "name": "名称", "email": "邮箱",
            "phone": "电话", "address": "地址", "city": "城市", "country": "国家",
            "date": "日期", "time": "时间", "price": "价格", "total": "总计",
            "quantity": "数量", "amount": "金额", "order": "订单", "product": "产品",
            "invoice": "发票", "employee": "员工", "artist": "艺术家", "album": "专辑",
            "track": "曲目", "genre": "流派", "playlist": "播放列表", "first": "名",
            "last": "姓", "company": "公司", "fax": "传真", "state": "州",
            "postal": "邮编", "code": "代码", "support": "客服", "rep": "代表",
            "birth": "生日", "hire": "入职", "title": "职位", "reports": "汇报",
            "billing": "账单", "unit": "单位", "media": "媒体", "type": "类型",
            "composer": "作曲", "milliseconds": "毫秒", "bytes": "字节"
        }
        
        # 尝试生成中文别名
        parts = snake_case.split("_")
        chinese_parts = [chinese_mappings.get(p, p) for p in parts]
        chinese_alias = "".join(chinese_parts)
        if chinese_alias != snake_case.replace("_", ""):
            aliases.append(chinese_alias)
        
        return list(set(aliases))
    
    def _generate_table_aliases(self, table_name: str) -> List[str]:
        """
        生成表名别名（用于模糊匹配）
        例如: Customer -> ["customer", "customers", "客户"]
        """
        aliases = [table_name.lower()]
        
        # 驼峰转下划线
        snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', table_name).lower()
        if snake_case != table_name.lower():
            aliases.append(snake_case)
        
        # 单复数转换
        lower_name = table_name.lower()
        if lower_name.endswith('s'):
            aliases.append(lower_name[:-1])  # 去掉 s
        else:
            aliases.append(lower_name + 's')  # 加上 s
        
        # 常见中文映射（支持多个别名）
        table_chinese = {
            "customer": ["客户", "顾客", "用户"],
            "employee": ["员工", "雇员", "职员"],
            "artist": ["艺术家", "歌手", "艺人"],
            "album": ["专辑", "唱片"],
            "track": ["曲目", "歌曲", "音轨"],
            "genre": ["流派", "类型", "风格"],
            "playlist": ["播放列表", "歌单"],
            "invoice": ["发票", "订单", "账单", "销售"],
            "invoiceline": ["发票明细", "订单明细", "订单项"],
            "mediatype": ["媒体类型", "格式"],
            "playlisttrack": ["播放列表曲目"]
        }
        
        # 尝试匹配中文（支持多个别名）
        for key, chinese_list in table_chinese.items():
            if key in lower_name:
                if isinstance(chinese_list, list):
                    aliases.extend(chinese_list)
                else:
                    aliases.append(chinese_list)
                break
        
        return list(set(aliases))
    
    def load_schema(self) -> Dict:
        """加载 schema.json"""
        if self._schema_cache:
            return self._schema_cache
        
        if not self.schema_path.exists():
            print(f"⚠️ Schema file not found, generating...")
            return self.generate_schema_json()
        
        with open(self.schema_path, "r", encoding="utf-8") as f:
            self._schema_cache = json.load(f)
            self._field_index = self._schema_cache.get("field_index", {})
        
        return self._schema_cache
    
    def search_fields(self, keyword: str, threshold: float = 0.6) -> List[Dict]:
        """
        根据关键词搜索匹配的字段
        
        Args:
            keyword: 搜索关键词
            threshold: 相似度阈值 (0-1)
            
        Returns:
            匹配的字段列表
        """
        schema = self.load_schema()
        matches = []
        keyword_lower = keyword.lower()
        
        for table in schema["tables"]:
            for col in table["columns"]:
                # 精确匹配
                if keyword_lower == col["name"].lower():
                    matches.append({
                        "table": table["name"],
                        "column": col["name"],
                        "type": col["type"],
                        "match_score": 1.0,
                        "match_type": "exact"
                    })
                    continue
                
                # 别名匹配
                if keyword_lower in [a.lower() for a in col.get("aliases", [])]:
                    matches.append({
                        "table": table["name"],
                        "column": col["name"],
                        "type": col["type"],
                        "match_score": 0.95,
                        "match_type": "alias"
                    })
                    continue
                
                # 模糊匹配
                score = SequenceMatcher(None, keyword_lower, col["name"].lower()).ratio()
                if score >= threshold:
                    matches.append({
                        "table": table["name"],
                        "column": col["name"],
                        "type": col["type"],
                        "match_score": score,
                        "match_type": "fuzzy"
                    })
        
        # 按匹配分数排序
        matches.sort(key=lambda x: x["match_score"], reverse=True)
        return matches
    
    def find_relevant_tables(self, question: str) -> List[str]:
        """
        根据问题找出相关的表
        
        Args:
            question: 用户问题
            
        Returns:
            相关表名列表
        """
        schema = self.load_schema()
        relevant_tables: Set[str] = set()
        question_lower = question.lower()
        
        # 1. 直接匹配表名和表名别名
        for table_name in schema["table_list"]:
            # 原表名匹配
            if table_name.lower() in question_lower:
                relevant_tables.add(table_name)
                continue
            
            # 表名别名匹配
            table_aliases = self._generate_table_aliases(table_name)
            for alias in table_aliases:
                if alias in question_lower:
                    relevant_tables.add(table_name)
                    break
        
        # 2. 匹配字段名和别名
        for table in schema["tables"]:
            for col in table["columns"]:
                # 检查字段名
                if col["name"].lower() in question_lower:
                    relevant_tables.add(table["name"])
                    break
                # 检查别名
                for alias in col.get("aliases", []):
                    if alias in question_lower:
                        relevant_tables.add(table["name"])
                        break
        
        # 3. 关键词匹配（扩展）
        keywords = re.findall(r'[\u4e00-\u9fa5]+|\b\w+\b', question_lower)
        for keyword in keywords:
            if len(keyword) < 2:  # 跳过太短的词
                continue
            matches = self.search_fields(keyword, threshold=0.7)
            for match in matches[:3]:  # 取前3个匹配
                relevant_tables.add(match["table"])
        
        return list(relevant_tables)
    
    def format_schema_for_prompt(self, tables: Optional[List[str]] = None, include_samples: bool = False) -> str:
        """
        格式化 Schema 供 prompt 使用
        
        Args:
            tables: 指定的表列表，None 表示全部
            include_samples: 是否包含示例值
            
        Returns:
            格式化的 schema 文本
        """
        schema = self.load_schema()
        
        lines = [
            f"数据库类型: {schema['database_type']}",
            f"",
            f"### 可用表清单",
            f"共 {len(schema['table_list'])} 个表: {', '.join(schema['table_list'])}",
            f"",
            f"### 表结构详情"
        ]
        
        target_tables = tables if tables else schema["table_list"]
        
        for table in schema["tables"]:
            if table["name"] not in target_tables:
                continue
            
            lines.append(f"\n**{table['name']}** ({table.get('row_count', '?')} 行)")
            
            if table.get("description"):
                lines.append(f"  描述: {table['description']}")
            
            lines.append("  字段:")
            for col in table["columns"]:
                pk_mark = " [PK]" if col["primary_key"] else ""
                nn_mark = " [NOT NULL]" if col["not_null"] else ""
                desc = f" - {col['description']}" if col.get("description") else ""
                
                col_line = f"    - {col['name']} ({col['type']}){pk_mark}{nn_mark}{desc}"
                
                if include_samples and col.get("sample_values"):
                    samples = ", ".join([str(v)[:20] for v in col["sample_values"][:3]])
                    col_line += f" 示例: [{samples}]"
                
                lines.append(col_line)
            
            # 外键信息
            if table.get("foreign_keys"):
                lines.append("  外键关系:")
                for fk in table["foreign_keys"]:
                    lines.append(f"    - {fk['column']} -> {fk['references_table']}.{fk['references_column']}")
        
        return "\n".join(lines)
    
    def get_smart_schema_for_question(self, question: str, max_tables: int = 5) -> str:
        """
        根据问题智能选择相关的 schema 信息
        
        Args:
            question: 用户问题
            max_tables: 最大返回表数量
            
        Returns:
            针对问题优化的 schema 文本
        """
        relevant_tables = self.find_relevant_tables(question)
        
        # 如果找到相关表，只返回这些表的 schema
        if relevant_tables:
            if len(relevant_tables) > max_tables:
                relevant_tables = relevant_tables[:max_tables]
            
            header = f"### 与问题相关的表 (共 {len(relevant_tables)} 个)\n"
            header += f"检测到问题可能涉及: {', '.join(relevant_tables)}\n"
            
            return header + "\n" + self.format_schema_for_prompt(
                tables=relevant_tables, 
                include_samples=True
            )
        
        # 如果没找到相关表，返回完整 schema（不含示例值以节省 token）
        return self.format_schema_for_prompt(include_samples=False)
    
    def build_relationship_graph(self) -> Dict[str, List[Dict]]:
        """
        构建表关系图（基于外键关系，双向连接）
        M8: 如果schema中没有外键信息，则动态推断
        
        Returns:
            关系图字典: {table_name: [{"table": ref_table, "via": fk_column, "references": ref_column}]}
        """
        schema = self.load_schema()
        graph = {}
        
        # 初始化所有表
        for table in schema["tables"]:
            graph[table["name"]] = []
        
        # 构建双向关系图
        for table in schema["tables"]:
            table_name = table["name"]
            
            # 获取外键信息（如果schema中没有，则推断）
            foreign_keys = table.get("foreign_keys", [])
            if not foreign_keys:
                # M8: 动态推断外键
                foreign_keys = self._infer_foreign_keys(table_name)
            
            # 添加出边（当前表的外键指向其他表）
            for fk in foreign_keys:
                ref_table = fk["references_table"]
                graph[table_name].append({
                    "table": ref_table,
                    "via": fk["column"],
                    "references": fk["references_column"],
                    "direction": "out"
                })
                
                # 同时添加反向边（双向图，方便BFS搜索）
                if ref_table in graph:
                    graph[ref_table].append({
                        "table": table_name,
                        "via": fk["references_column"],
                        "references": fk["column"],
                        "direction": "in"
                    })
        
        return graph
    
    def find_join_path(self, tables: List[str]) -> Optional[List[Dict]]:
        """
        找到连接多个表的最短路径（使用BFS算法）
        
        Args:
            tables: 需要连接的表列表
            
        Returns:
            JOIN步骤列表，每个步骤包含：
            {
                "from_table": str,
                "join_table": str,
                "join_type": str,  # "INNER", "LEFT", "RIGHT"
                "condition": str,   # "table1.id = table2.foreign_id"
                "via_column": str,  # 连接使用的列
                "references_column": str
            }
        """
        if len(tables) < 2:
            return None
        
        graph = self.build_relationship_graph()
        schema = self.load_schema()
        
        # 如果只有一个表，不需要JOIN
        if len(tables) == 1:
            return []
        
        # 使用BFS找到表之间的最短路径
        def bfs_shortest_path(start: str, end: str) -> Optional[List[str]]:
            """BFS查找两个表之间的最短路径"""
            if start == end:
                return [start]
            
            queue = [(start, [start])]
            visited = {start}
            
            while queue:
                current, path = queue.pop(0)
                
                # 检查直接连接
                if current in graph:
                    for neighbor in graph[current]:
                        neighbor_table = neighbor["table"]
                        if neighbor_table == end:
                            return path + [end]
                        
                        if neighbor_table not in visited:
                            visited.add(neighbor_table)
                            queue.append((neighbor_table, path + [neighbor_table]))
            
            return None
        
        # 构建表之间的连接路径
        join_steps = []
        connected_tables = [tables[0]]  # 从第一个表开始
        
        for target_table in tables[1:]:
            # 找到target_table到已连接表的路径
            best_path = None
            best_start = None
            
            for connected_table in connected_tables:
                path = bfs_shortest_path(connected_table, target_table)
                if path and (best_path is None or len(path) < len(best_path)):
                    best_path = path
                    best_start = connected_table
            
            if not best_path:
                # 如果找不到路径，尝试反向查找
                for connected_table in connected_tables:
                    path = bfs_shortest_path(target_table, connected_table)
                    if path:
                        best_path = list(reversed(path))
                        best_start = connected_table
                        break
            
            if not best_path:
                # 无法找到连接路径
                print(f"⚠️  警告: 无法找到表 {target_table} 到其他表的连接路径")
                continue
            
            # 生成JOIN步骤
            for i in range(len(best_path) - 1):
                from_table = best_path[i]
                to_table = best_path[i + 1]
                
                # 查找连接条件
                join_condition = self._find_join_condition(from_table, to_table, schema)
                if not join_condition:
                    continue
                
                # 确定JOIN类型（默认INNER JOIN）
                join_type = self._determine_join_type(from_table, to_table, schema)
                
                join_steps.append({
                    "from_table": from_table,
                    "join_table": to_table,
                    "join_type": join_type,
                    "condition": join_condition["condition"],
                    "via_column": join_condition["via_column"],
                    "references_column": join_condition["references_column"]
                })
            
            # 更新已连接的表
            connected_tables.append(target_table)
            # 添加路径中间的表
            for table in best_path[1:-1]:
                if table not in connected_tables:
                    connected_tables.append(table)
        
        return join_steps if join_steps else None
    
    def _find_join_condition(self, table1: str, table2: str, schema: Dict) -> Optional[Dict]:
        """
        查找两个表之间的连接条件
        M8: 如果schema中没有外键信息，则动态推断
        """
        # 获取table1的外键信息（如果schema中没有，则推断）
        table1_obj = None
        for table in schema["tables"]:
            if table["name"] == table1:
                table1_obj = table
                break
        
        if table1_obj:
            foreign_keys = table1_obj.get("foreign_keys", [])
            if not foreign_keys:
                # M8: 动态推断外键
                foreign_keys = self._infer_foreign_keys(table1)
            
            # 检查table1的外键是否指向table2
            for fk in foreign_keys:
                if fk["references_table"].lower() == table2.lower():
                    return {
                        "condition": f"{table1}.{fk['column']} = {table2}.{fk['references_column']}",
                        "via_column": fk["column"],
                        "references_column": fk["references_column"]
                    }
        
        # 获取table2的外键信息（如果schema中没有，则推断）
        table2_obj = None
        for table in schema["tables"]:
            if table["name"] == table2:
                table2_obj = table
                break
        
        if table2_obj:
            foreign_keys = table2_obj.get("foreign_keys", [])
            if not foreign_keys:
                # M8: 动态推断外键
                foreign_keys = self._infer_foreign_keys(table2)
            
            # 检查table2的外键是否指向table1
            for fk in foreign_keys:
                if fk["references_table"].lower() == table1.lower():
                    return {
                        "condition": f"{table1}.{fk['references_column']} = {table2}.{fk['column']}",
                        "via_column": fk["references_column"],
                        "references_column": fk["column"]
                    }
        
        return None
    
    def _determine_join_type(self, table1: str, table2: str, schema: Dict) -> str:
        """
        确定JOIN类型
        默认使用INNER JOIN，如果外键允许NULL则使用LEFT JOIN
        """
        # 检查外键是否允许NULL
        for table in schema["tables"]:
            if table["name"] == table2:
                for fk in table.get("foreign_keys", []):
                    if fk["references_table"] == table1:
                        # 查找外键列的定义
                        for col in table["columns"]:
                            if col["name"] == fk["column"]:
                                # 如果外键允许NULL，使用LEFT JOIN
                                if not col.get("not_null", True):
                                    return "LEFT"
                                break
        
        # 默认使用INNER JOIN
        return "INNER"
    
    def format_join_suggestions(self, tables: List[str]) -> str:
        """
        格式化JOIN路径建议，用于添加到Prompt中
        
        Args:
            tables: 涉及的表列表
            
        Returns:
            格式化的JOIN建议文本
        """
        if len(tables) < 2:
            return ""
        
        join_steps = self.find_join_path(tables)
        if not join_steps:
            return f"## 表关系提示\n涉及的表: {', '.join(tables)}\n注意: 无法自动找到表之间的连接路径，请根据业务逻辑手动确定JOIN条件。\n"
        
        lines = [
            "## 表关系与JOIN路径建议",
            f"### 涉及的表 ({len(tables)} 个)",
            ", ".join(tables),
            "",
            "### JOIN路径建议",
            f"主表: {tables[0]}",
            ""
        ]
        
        for i, step in enumerate(join_steps, 1):
            join_type = step["join_type"]
            lines.append(f"{i}. {join_type} JOIN {step['join_table']}")
            lines.append(f"   条件: {step['condition']}")
            lines.append("")
        
        lines.append("### 注意事项")
        lines.append("- 建议使用表别名（如 customer c, invoice i）")
        lines.append("- 确保JOIN条件正确匹配外键关系")
        lines.append("- 根据业务需求选择合适的JOIN类型（INNER/LEFT/RIGHT）")
        
        return "\n".join(lines)


# 全局实例
schema_manager = SchemaManager()



