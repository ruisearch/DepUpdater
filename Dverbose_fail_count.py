"""计算-Dverbose失败的module数"""
import os

def find_and_read_verbose_tree(directory):
    count = 0
    for root, _, files in os.walk(directory):
        if "verbose_tree.txt" in files:
            file_path = os.path.join(root, "verbose_tree.txt")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if Dverbose_succ(content) == False:
                print(file_path)
                count += 1
    print(count)
    return count
def Dverbose_succ(content):
    if 'BUILD SUCCESS' in content:
        if 'omitted for conflict with'  in content:
            return True
        if 'omitted for duplicate' in content:
            return True
        if 'version managed from' in content:
            return True
        return False
    return True

tree_dir = os.path.join('data', 'tree')
find_and_read_verbose_tree(tree_dir)