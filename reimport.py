# -*- coding: utf-8 -*-
import sys
import imp
import inspect
import traceback

_ignore_attrs = {
  '__module__', '_reload_all', '__dict__', '__weakref__', '__doc__',
}

class Finder(object):
    def find_module(self, fullname, path):
        self.backup_module(fullname)
        fd, path, des = imp.find_module(fullname.split('.')[-1], path)
        module = imp.load_module(fullname, fd, path, des)
        print "Finder name=%s, mid=%s"%(fullname, id(module))
        if module:
            self.update_module(module, sys.old_module_attrs[fullname])
            return Loader(module)
        return None

    def load_module(self, fullname):
        print 'Loader name=%s, mid=%s'%(fullname, )

    def backup_module(self, fullname):
        old_module = sys.modules.pop(fullname)
        sys.old_modules[fullname] = old_module
        sys.old_module_attrs[fullname] = dict(old_module.__dict__)
        sys.modules[fullname] = old_module

    def update_module(self, module, old_attrs):
        if not old_attrs:
            return
        for name, attr in inspect.getmembers(module):
            if isinstance(attr, type) and attr is not type:
                old_class = old_attrs.get(name)
                if old_class:
                    self.update_class(old_class, attr, getattr(attr, '_reload_all', False))
                    setattr(module, name, old_class)
            elif inspect.isfunction(attr):
                old_func = old_attrs.get(name)
                if not self.update_func(old_func, attr):
                    old_attrs[name] = attr
                else:
                    setattr(module, name, old_func)

        if getattr(module, '_reload_all', False):
            module.__dict__.update(old_attrs)

    def update_class(self, old_class, new_class, reload_all=False):
        for name, attr in old_class.__dict__.items():
            if name in new_class.__dict__:
                continue
            if not inspect.isfunction(attr):
                continue
            type.__delattr__(old_class, name)

        for name, attr in new_class.__dict__.iteritems():
            if name not in old_class.__dict__:
                setattr(old_class, name, attr)
                continue
            old_attr = old_class.__dict__[name]
            new_attr = attr
            if inspect.isfunction(old_attr) and inspect.isfunction(new_attr):
                if not self.update_func(old_attr, new_attr):
                    setattr(old_class, name, new_attr)
            elif isinstance(new_attr, staticmethod) or isinstance(new_attr, classmethod):
                if not self.update_func(old_attr.__func__, new_attr.__func__):
                    old_attr.__func__ = new_attr.__func__
            elif reload_all and name not in _ignore_attrs:
                setattr(old_class, name, new_attr)

    def update_func(self, old_func, new_func, update_cell_depth=2):
        old_cell_num = len(old_func.func_closure) if old_func.func_closure else 0
        new_cell_num = len(new_func.func_closure) if new_func.func_closure else 0
        if old_cell_num != new_cell_num:
            return False
        setattr(old_func, 'func_code', new_func.func_code)
        setattr(old_func, 'func_defaults', new_func.func_defaults)
        setattr(old_func, 'func_doc', new_func.func_doc)
        setattr(old_func, 'func_dict', new_func.func_dict)
        if old_cell_num < 1 or update_cell_depth < 1:
            return True
        for idx, cell in enumerate(old_func.func_closure):
            if inspect.isfunction(cell.cell_contents):
                self.update_func(cell.cell_contents, new_func.func_closure[idx].cell_contents, update_cell_depth-1)
        return True

class Loader(object):
    def __init__(self, module):
        self._module = module

    def load_module(self, name):
        print 'Loader name=%s, mid=%s'%(name, id(self._module))
        return self._module

sys.meta_path.append(Finder())

def reimport(fullname):
    print '--------------------- start reload -----------------------'
    sys.old_modules = {}
    sys.old_module_attrs = {}
    try:
        __import__(fullname)
    except:
        traceback.print_exc()
        print 'error import module %s' % fullname
    print '--------------------- finish reload -----------------------'

