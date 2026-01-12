"""
项目管理模块 - 支持保存、加载、导出项目

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""
import json
import os
import re
import tempfile
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path

from novel_generator import NovelProject, Chapter

logger = logging.getLogger(__name__)

PROJECTS_DIR = "projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)


class ProjectManager:
    """项目管理器"""
    
    @staticmethod
    def _slugify(name: str) -> str:
        s = str(name or "").lower()
        s = re.sub(r'[^a-z0-9]+', '-', s)
        s = s.strip('-')
        return s or 'project'

    @staticmethod
    def create_project(
        title: str,
        genre: str,
        character_setting: str,
        world_setting: str,
        plot_idea: str
    ) -> Tuple[Optional[NovelProject], str]:
        """
        创建新项目
        
        Returns:
            (项目对象, 状态信息)
        """
        if not title or not title.strip():
            return None, "项目标题不能为空"
        
        if not genre or not genre.strip():
            return None, "小说类型不能为空"
        
        project = NovelProject(
            title=title.strip(),
            genre=genre.strip(),
            character_setting=character_setting.strip(),
            world_setting=world_setting.strip(),
            plot_idea=plot_idea.strip()
        )
        
        logger.info(f"创建项目: {title}")
        return project, "项目创建成功"
    
    @staticmethod
    def save_project(project: NovelProject) -> Tuple[bool, str]:
        """
        保存项目到磁盘（原子写入）
        
        Returns:
            (成功标志, 状态信息)
        """
        try:
            if not project or not project.title:
                return False, "项目信息不完整"

            # 使用已有 project.id 保持稳定，否则生成 slug（首次保存生成并设置 project.id）
            if getattr(project, 'id', None):
                project_id = project.id
            else:
                slug = ProjectManager._slugify(project.title)
                candidate = slug
                candidate_path = os.path.join(PROJECTS_DIR, candidate)
                if os.path.exists(candidate_path):
                    candidate = f"{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                project_id = candidate
                project.id = project_id

            project_dir = os.path.join(PROJECTS_DIR, project_id)
            os.makedirs(project_dir, exist_ok=True)

            # 保存项目元数据（写入临时文件后原子替换）
            metadata = {
                "id": project_id,
                "title": project.title,
                "genre": project.genre,
                "character_setting": project.character_setting,
                "world_setting": project.world_setting,
                "plot_idea": project.plot_idea,
                "created_at": project.created_at,
                "updated_at": datetime.now().isoformat(),
                "chapters": [ch.to_dict() for ch in project.chapters]
            }

            metadata_file = os.path.join(project_dir, "metadata.json")
            tmp_meta = None
            try:
                with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=project_dir) as tmp:
                    json.dump(metadata, tmp, ensure_ascii=False, indent=4)
                    tmp_meta = tmp.name
                os.replace(tmp_meta, metadata_file)
            except Exception as e:
                if tmp_meta and os.path.exists(tmp_meta):
                    try:
                        os.remove(tmp_meta)
                    except Exception:
                        pass
                raise

            # 保存小说文本（如果有章节）
            if project.chapters:
                novel_text = f"# {project.title}\n\n"
                for chapter in project.chapters:
                    if chapter.content:
                        novel_text += f"## 第{chapter.num}章 {chapter.title}\n\n"
                        novel_text += chapter.content + "\n\n"

                novel_file = os.path.join(project_dir, "novel.md")
                tmp_novel = None
                try:
                    with tempfile.NamedTemporaryFile('w', encoding='utf-8', delete=False, dir=project_dir) as tmp:
                        tmp.write(novel_text)
                        tmp_novel = tmp.name
                    os.replace(tmp_novel, novel_file)
                except Exception as e:
                    if tmp_novel and os.path.exists(tmp_novel):
                        try:
                            os.remove(tmp_novel)
                        except Exception:
                            pass
                    raise

            logger.info(f"项目已保存: {project_id}")
            return True, f"项目已保存: {project_id}"

        except Exception as e:
            logger.error(f"项目保存失败: {e}")
            return False, f"项目保存失败: {str(e)}"
    
    @staticmethod
    def load_project(project_id: str) -> Tuple[Optional[NovelProject], str]:
        """
        加载项目
        
        Returns:
            (项目对象, 状态信息)
        """
        try:
            project_dir = os.path.join(PROJECTS_DIR, project_id)
            
            if not os.path.exists(project_dir):
                return None, f"项目不存在: {project_id}"
            
            metadata_file = os.path.join(project_dir, "metadata.json")
            
            if not os.path.exists(metadata_file):
                return None, "项目元数据文件损坏"
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # 重建项目对象
            project = NovelProject(
                title=metadata.get("title", ""),
                genre=metadata.get("genre", ""),
                character_setting=metadata.get("character_setting", ""),
                world_setting=metadata.get("world_setting", ""),
                plot_idea=metadata.get("plot_idea", ""),
                created_at=metadata.get("created_at", ""),
                updated_at=metadata.get("updated_at", "")
            )
            
            # 加载章节
            for ch_data in metadata.get("chapters", []):
                chapter = Chapter(
                    num=ch_data.get("num", 0),
                    title=ch_data.get("title", ""),
                    desc=ch_data.get("desc", ""),
                    content=ch_data.get("content", ""),
                    word_count=ch_data.get("word_count", 0),
                    generated_at=ch_data.get("generated_at", "")
                )
                project.chapters.append(chapter)
            
            logger.info(f"项目已加载: {project_id}")
            return project, "项目加载成功"
        
        except Exception as e:
            logger.error(f"项目加载失败: {e}")
            return None, f"项目加载失败: {str(e)}"
    
    @staticmethod
    def list_projects() -> List[Dict]:
        """
        列出所有项目
        
        Returns:
            项目信息列表 [{"id": "...", "title": "...", "genre": "...", "created_at": "...", "updated_at": "..."}]
        """
        try:
            projects = []
            
            if not os.path.exists(PROJECTS_DIR):
                return projects
            
            for project_id in os.listdir(PROJECTS_DIR):
                project_dir = os.path.join(PROJECTS_DIR, project_id)
                
                if not os.path.isdir(project_dir):
                    continue
                
                metadata_file = os.path.join(project_dir, "metadata.json")
                
                if not os.path.exists(metadata_file):
                    continue
                
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    projects.append({
                        "id": project_id,
                        "title": metadata.get("title", "未命名"),
                        "genre": metadata.get("genre", ""),
                        "created_at": metadata.get("created_at", ""),
                        "updated_at": metadata.get("updated_at", ""),
                        "chapter_count": len(metadata.get("chapters", [])),
                        "completed_chapters": sum(1 for ch in metadata.get("chapters", []) if ch.get("content", "").strip())
                    })
                except Exception as e:
                    logger.warning(f"读取项目元数据失败 {project_id}: {e}")
            
            # 按更新时间排序
            projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            
            logger.info(f"找到 {len(projects)} 个项目")
            return projects
        
        except Exception as e:
            logger.error(f"列出项目失败: {e}")
            return []
    

    @staticmethod
    def get_project_by_title(project_title: str) -> Optional[Dict]:
        """
        按标题获取项目信息

        Returns:
            项目字典 或 None
        """
        projects = ProjectManager.list_projects()
        for project in projects:
            if project.get("title") == project_title:
                return project
        return None

    @staticmethod
    def delete_project(project_id: str) -> Tuple[bool, str]:
        """
        删除项目
        
        Returns:
            (成功标志, 状态信息)
        """
        try:
            project_dir = os.path.join(PROJECTS_DIR, project_id)
            
            if not os.path.exists(project_dir):
                return False, f"项目不存在: {project_id}"
            
            import shutil
            shutil.rmtree(project_dir)
            
            logger.info(f"项目已删除: {project_id}")
            return True, f"项目已删除: {project_id}"
        
        except Exception as e:
            logger.error(f"项目删除失败: {e}")
            return False, f"项目删除失败: {str(e)}"
    
    @staticmethod
    def export_project(project: NovelProject, export_format: str = "json") -> Tuple[Optional[str], str]:
        """
        导出项目配置（用于分享或备份）
        
        Args:
            project: 项目对象
            export_format: 导出格式 (json/zip)
        
        Returns:
            (文件路径, 状态信息)
        """
        try:
            if not project:
                return None, "项目为空"
            
            backup_dir = os.path.join(PROJECTS_DIR, "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            if export_format == "json":
                data = {
                    "title": project.title,
                    "genre": project.genre,
                    "character_setting": project.character_setting,
                    "world_setting": project.world_setting,
                    "plot_idea": project.plot_idea,
                    "created_at": project.created_at,
                    "chapters": [ch.to_dict() for ch in project.chapters]
                }
                
                filename = f"{project.title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(backup_dir, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                logger.info(f"项目已导出: {filename}")
                return filepath, f"项目已导出: {filename}"
            
            else:
                return None, f"不支持的导出格式: {export_format}"
        
        except Exception as e:
            logger.error(f"项目导出失败: {e}")
            return None, f"项目导出失败: {str(e)}"


def get_project_manager() -> ProjectManager:
    """获取项目管理器实例"""
    return ProjectManager()
