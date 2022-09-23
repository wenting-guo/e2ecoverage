import re
import sys
from md_utils import mdtable2array

def replace_state(ori_item,columns):
    new_item = ori_item
    for col in columns:
        ori_value = ori_item.get(col)
        if ori_value and ori_value.find("[x]") != -1:
            # this item was checked
            new_item[col] = ori_value.replace('[ ]','[x]')
    return new_item

def merge(template_file, target_file):
    header, segment, template = mdtable2array(template_file)
    _, _, target = mdtable2array(target_file)
    with  open(target_file, 'w') as f:
        f.write(header+"\n")
        f.write(segment+"\n")
        for it_temp in template:
            category1 = it_temp["category"]
            id1 = it_temp["ID"]
            newline = it_temp
            # matched is the line of target file which matches the category+ID
            matched = [ x for x in target if x["category"] == category1 and x["ID"] == id1 ]
            if len(matched) > 0 :
                # this item exists in original target file, keep its result when checked
                newline = replace_state(matched[0],["description","fulfilled"])
            else:
                #this is a newly added item
                print("DEBUG: newly add item:", category1, "-", id1)
                newline["fulfilled"] = newline["fulfilled"] + "(new)"
            plaintext="|"
            for _,v in newline.items():
                plaintext += v + "|"
            f.write(plaintext+'\n')

if __name__=='__main__':
    merge(template_file=sys.argv[1], target_file=sys.argv[2])
