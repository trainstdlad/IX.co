from re import compile as re_comp, I
from typing import Dict
from sys import exit as sys_exit

 
 
def main():
    line_re = re_comp(r'^(dev|prod|uat|qa)-(projects1/projects2/projects3).* - (\d+)$', I)
    data: Dict = dict()
    try:
        with open('report.txt') as report:
            for line in report:
                match = line_re.match(line)
                if match:
                    if match.group(2) in data:
                        data[match.group(2)] += float(match.group(3)) / 1024 / 1024 / 1024
                    else:
                        data[match.group(2)] = float(match.group(3)) / 1024 / 1024 / 1024
    except OSError as err:
        print('Could not open/read file report.txt: ', err)
        sys_exit(1)
    try:
        with open('summaryOfproject.txt', 'w') as summary_of_project:
            for proj in data:
                summary_of_project.write(f'{proj} {data[proj]}\n')
    except OSError as err:
        print('Could not open/write file summaryOfproject.txt: ', err)
        sys_exit(2)
 
if __name__ == '__main__':
    main()
