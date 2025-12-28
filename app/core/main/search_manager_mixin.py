"""搜索管理混入类 - 重构版"""

class SearchManagerMixin:
    """搜索管理混入类 - 处理搜索功能"""
    
    def show_search_options(self):
        return self.search_manager.show_search_options()
        
    def search_text(self):
        return self.search_manager.search_text()
        
    def search_next(self):
        return self.search_manager.search_next()
        
    def search_previous(self):
        return self.search_manager.search_previous()