import os
import re
from queue import Queue
import copy
alpha_dic = {}
for i in range(26):
    alpha_dic[i+1] = chr(97+i)
# 正则表达式：谓词、谓词符号、谓词参数
FOP = r"~?[A-Z]+[a-zA-z]*\([a-z,\s]+\)"
PREDICATE_SYMBLE = r"~?[A-Z]+[a-zA-Z]*"
PARAMETER_SYMBLE = r"([a-z]+)"
characters = "abcdefghijklmnopqrstuvwxyz"


class Predicate:
    """
    一阶逻辑谓词
    """

    def __init__(self, content: list, is_neg: bool):
        self.symble = content[0]  # 符号
        self.parameters = content[1:]  # 参数
        self.is_neg = is_neg #正负

    def __str__(self):
        """
        定义 __str__ 运算符，输出为字符串形式
        """
        prefix = "~" if self.is_neg else "" #如果有符号加“~”
        return prefix + self.symble + "(" + ", ".join(self.parameters) + ")"

    def neg(self):
        """
        返回当前谓词的否定形式（Predicate 对象）。
        情况1、本身是否定形式
        情况2、本身不是否定形式
        """
        new_content = [self.symble] + self.parameters
        return Predicate(new_content, is_neg = not self.is_neg)

    def __eq__(self, other):
        """
        定义 == 运算符，当谓词符号相等且参数均相同时返回True，否则False
        """
        if type(other) != Predicate:
            raise TypeError("The type of the parameter is not Predicate")
        return self.symble == other.symble and self.parameters == other.parameters and self.is_neg == other.is_neg


class Clause:
    """
    一阶逻辑子句，由多个谓词组成
    """

    def __init__(self, raw: str):
        self.predicates = []
        items = re.findall(FOP, raw) #找谓词
        for item in items:
            name_part = item.split('(')[0] 
            param_part = item[item.find('(')+1:item.find(')')] 
            sym_match = re.search(PREDICATE_SYMBLE, name_part)
            symble = sym_match.group() if sym_match else ""
            parameters = re.findall(PARAMETER_SYMBLE, param_part)
            is_neg = False
            if symble.startswith("~"):
                is_neg = True
                symble = symble[1:]
            new_predicate = Predicate([symble]+parameters, is_neg) #组成新谓词
            self.predicates.append(new_predicate) 

        """
        Input:
            - raw: Type: str 子句以字符串形式传入
        """
        """
        存储 clause 的所有 predicate
        步骤1、使用 re 匹配谓词
        步骤2、使用 re 匹配谓词符号
        步骤3、使用 re 匹配谓词参数
        """

    def __str__(self):
        """
        定义 __str__ 运算符，输出为字符串形式
        """
        return "(" + ",".join([p.__str__() for p in self.predicates]) + ")" #以逗号分隔每个谓词并组成字符串

    def __eq__(self, other):
        """
        定义 == 运算符，当两个子句的谓词均相同时返回True，否则False
        """
        if type(other) != Clause:
            raise TypeError("The type of the parameter is not Clause")
        return self.predicates == other.predicates

    def __bool__(self):
        """
        定义布尔运算符的行为，当谓词列表为空时返回False，否则True
        """
        return len(self.predicates) > 0

    def __len__(self):
        """
        定义长度运算符的行为，返回谓词列表的长度
        """
        return len(self.predicates)


class KnowledgeBase:
    def __init__(self, path):
        with open(path, "r") as f:
            content = [l.strip() for l in f.readlines()]

            content.remove("KB:")
            content.remove("QUERY:")
            self.clauses = [self.read_clause(clause) for clause in content]
            # for clause in self.clauses:
            #     print(clause)

        # 归结历史
        # key: (i子句号, j子句号, ki谓词位置, kj谓词位置)
        # value: (assigment合一替换, idx新子句)
        self.history = {}

    def read_clause(self, raw_clause: str) -> Clause:
        """
        将单一子句转化为子句类的形式
        """
        if raw_clause[0] == "(":
            raw_clause = raw_clause[1:-1]  # 取出多个谓词子句的外层括号
        return Clause(raw_clause)
    
    
    def resolution(self) -> bool:
        """
        归结当前数据库
        """
        history_check = set() #检查重复
        i = 0
        while i < len(self.clauses):
            j = 0
            while j < i:
                if (j, i) in history_check:
                    j+=1
                    continue
                history_check.add((j, i))
                c1 = self.clauses[i]
                c2 = self.clauses[j]
                success, ki, kj = check_resolution(c1, c2) #是否可归结，归结index
                if success:
                    Over = False
                    assignment = mgu(c1.predicates[ki], c2.predicates[kj]) #替换表
                    if assignment is not None:
                        new_clause = unify(c1, c2, assignment, ki, kj) #替换后的新子句
                        for c in self.clauses:
                            if c.__str__() == new_clause.__str__():  
                                Over = True
                        if Over == True: 
                            j+=1
                            continue #检查重复
                        new_index = len(self.clauses) #新子句index
                        self.history[new_index] = (i, j, assignment, ki, kj, new_clause.__str__()) #历史(父子句index，替换表，谓词下标,新子句)
                        self.clauses.append(new_clause)
                        if len(new_clause.predicates) == 0: #检查空列表
                            return True
                j+=1
            i+=1

        return False

        """
        循环完成数据库的归结
        1、遍历子句对，判断是否可以进行归结，获得可以归结的谓词下标（使用 check_resolution 函数）
        2、如果可以进行归结，检查归结历史
        3、如果不存在归结记录，计算 mgu（使用 mgu 函数），归结获得新子句（使用 unify 函数）
        4、添加归结历史记录，添加新子句
        5、如果归结得到空子句，返回True
        6、如果无法继续归结，返回False
        （可选）剪枝算法：通过控制新子句的长度进行剪枝
        """

    def path(self) -> list:
        """
        根据当前KB的推导记录，使用层次遍历算法找到空子句的推导路径
        """
        if not self.clauses or self.clauses[-1].predicates.__len__()!=0 :
            return []
        target_index = len(self.clauses)-1
        res_path = []
        target_list = [target_index]
        seen = set()
        while target_list:
            id = target_list.pop(0)
            if id in seen: continue
            seen.add(id)
            if id in self.history:
                i, j, assignment, ki, kj, new_clause_str = self.history[id]
                instead_str = ",".join([f"{k} = {v}" for k, v in assignment.items()])
                path_str = f"R[{i+1}{alpha_dic[ki+1]}, {j+1}{alpha_dic[kj+1]}]({instead_str}) = {new_clause_str} -- {id+1}"
                res_path.append(path_str)
                target_list.append(i)
                target_list.append(j)
        
        return res_path

        """
        1、如果末尾子句不是空子句，返回空列表
        2、根据 self.history 得到 新子句 与 父子句 的关系
        3、基于空子句，使用队列实现 BFS，反向追踪父子句
        4、返回推导路径列表

        推导路径格式示例：
        R[1a, 5a](x=mike) = (S(mike),C(mike)) -- 13
        其中：
        R[1a, 5a] 代表归结
        (x=mike) 代表合一替换
        (S(mike),C(mike)) 代表新子句
        13 代表新子句编号
        """


def is_variable(symbol: str) -> bool:
    """
    判断一个符号是否为变量，约定变量以小写字母表示，且长度不超过1
    """
    return len(symbol) == 1 and symbol.islower()#小写返回true


def check_resolution(clause1: Clause, clause2: Clause) -> tuple[bool, int, int]:
    """
    扫描子句中的所有谓词，判断两个子句是否可以进行归结
    """
    for i in range(len(clause1.predicates)):
        for j in range(len(clause2.predicates)):
            predi1 = clause1.predicates[i]
            predi2 = clause2.predicates[j]
            if predi1.symble == predi2.symble and predi1.is_neg != predi2.is_neg: #谓词相同正负不同则可以归结
                res_sub = mgu(predi1, predi2)
                if res_sub!=None:
                    return True, i, j #i, j为谓词下标
            else: continue
    return False, None, None


    """
    可以归结返回：
    (True, clause1可以归结的谓词下标, clause2可以归结的谓词下标)
    不可以归结返回：
    (False, None, None)
    """


def occurs_check(var: str, term: str, substitution: dict) -> bool:
    """
    检查变量是否出现在项中（occurs check），防止无限递归
    """
    if var == term: #var和term相等会导致无限递归
        return True
    if term in substitution:
        return occurs_check(var, substitution[term], substitution) #检查substitution[term]是否在替换表里且对应的替换是否是var
    return False

    """
    当存在循环替换时：return True
    当不存在循环替换时：return False

    循环替换示例：
    {"x": "y", "y": "x"}
    """


def apply_substitution(term: str, substitution: dict) -> str:
    """
    对项应用当前的替换
    """
    """
    返回替换完成的 term
    """
    return substitution[term] if term in substitution else term 


def mgu(p1: Predicate, p2: Predicate):
    """
    找到两个同名谓词中的最一般合一
    """
    #若谓词不相同或参数不同返回None
    if p1.symble!=p2.symble or len(p1.parameters)!=len(p2.parameters):
        return None
    substitution = {} #替换表
    for i in range(len(p1.parameters)):
        term1 = p1.parameters[i]
        term2 = p2.parameters[i]
        term1 = apply_substitution(term1, substitution)
        term2 = apply_substitution(term2, substitution)
        if term1 != term2: 
            if is_variable(term1): #term1是变量
                if not occurs_check(term1, term2, substitution): #循环判断
                    substitution[term1] = term2 #替换表里参数term1对应term2
                else: return None
            elif is_variable(term2): #term2是变量
                if not occurs_check(term2, term1, substitution):
                    substitution[term2] = term1 #替换表里参数term2对应term1
                else: return None
            else: return None
    return substitution


    """
    1、遍历相同位置参数对
    2、应用当前已经存在的替换
    3、分类讨论：
        3.1、当p1_k和p2_k相等时：
        3.2、当p1_k或p2_k是变量时：
        3.3、其他：
    """


def unify(c1: Clause, c2: Clause, assignment: dict, ki: int, kj: int) -> Clause:
    """
    根据 mgu 对两个子句进行归结
    """
    #将ki,kj下标的谓词删除
    """"
    用集合记录添加的谓词
    """
    seen_ptr = set() 
    new_predicates:list[Predicate] = []
    for i, predi in enumerate(c1.predicates):
        if i!=ki:
            """"
            记录
            """
            seen_ptr.add(predi.__str__())
            new_predicates.append(copy.deepcopy(predi))
    
    for j, predi in enumerate(c2.predicates):
        """"
        去重
        """
        if j!=kj and predi.__str__() not in seen_ptr:
            seen_ptr.add(predi.__str__())
            new_predicates.append(copy.deepcopy(c2.predicates[j]))
    #替换参数
    for p in new_predicates:
        for i in range(len(p.parameters)):
            term = p.parameters[i]
            if term in assignment:
                p.parameters[i] = assignment[term] #根据替换表修改参数
    if not new_predicates:
        return Clause("NIL")
    
    new_clause = Clause("")
    new_clause.predicates = new_predicates
    return new_clause
    
    """
    assignment：替换
    ki：子句1需要归结的谓词下标
    kj：子句2需要归结的谓词下标

    tip：
    1、需要归结的谓词下标互相抵消，所以处理不需要归结的谓词，得到新子句
    2、注意深拷贝的问题
    """


def main():
    #kb = KnowledgeBase("./test1.txt")
    #kb = KnowledgeBase("./test2.txt")
    kb = KnowledgeBase("./test3.txt")
    ans = kb.resolution()
    #if ans:
    path = kb.path()
    path.reverse()
    for idx, clause in enumerate(kb.clauses):
        print(str(idx+1) + ":", clause)
    for p in path:
        print(p)


if __name__ == "__main__":
    main()
