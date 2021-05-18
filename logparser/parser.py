"""
Log parsing for Datadog sum by company
"""
from argparse import ArgumentParser
from sys import exit as sys_exit
import pandas as pd


def get_arguments():
    """
    Get command line arguments
    """
    parser = ArgumentParser()
    parser.add_argument('-f', '--logs-file', dest='logfile', type=str, default='logs.csv')
    return vars(parser.parse_args())


def main():
    """
    Main function
    """
    args = get_arguments()
    try:
        csvframe = pd.read_csv(args.get('logfile'), usecols=[3, 5])
    except IOError as error:
        print(f"Can't read the file: {error}")
        sys_exit(1)
    result = dict()
    for _, row in csvframe.iterrows():
        if not result.get(row['Org']):
            result[row['Org']] = 0
        result[row['Org']] += row['Live Indexed']
    for key in result:
        print(f"{key} {result[key]}")


if __name__ == "__main__":
    main()
