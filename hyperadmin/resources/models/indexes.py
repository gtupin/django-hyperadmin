from hyperadmin.indexes import Index


class ModelIndex(Index):
    @property
    def model(self):
        return self.resource.model
    
    #def get_active_section(self):
    #    return self.sections['filter']
    
    def get_paginator_kwargs(self):
        return {'per_page':self.resource.list_per_page,}
    
    def get_links(self):
        links = super(ModelIndex, self).get_links()
        #links += self.getchangelist_sort_links()
        return links
    
    def get_changelist_sort_links(self):
        links = list()
        changelist = self.state['changelist']
        from django.contrib.admin.templatetags.admin_list import result_headers
        for header in result_headers(changelist):
            if header.get("sortable", False):
                prompt = unicode(header["text"])
                classes = ["sortby"]
                if "url" in header:
                    links.append(self.get_link(url=header["url"], prompt=prompt, classes=classes+["primary"], rel="sortby"))
                else:
                    if header["ascending"]:
                        classes.append("ascending")
                    if header["sorted"]:
                        classes.append("sorted")
                    links.append(self.get_link(url=header["url_primary"], prompt=prompt, classes=classes+["primary"], rel="sortby"))
                    links.append(self.get_link(url=header["url_remove"], prompt=prompt, classes=classes+["remove"], rel="sortby"))
                    links.append(self.get_link(url=header["url_toggle"], prompt=prompt, classes=classes+["toggle"], rel="sortby"))
        return links

