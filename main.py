import os,sys
import time
import argparse, textwrap
from Set import *
from Clause import *
from PatternSolver import *
from InputReader import InputReader
import configs
import traceback

# todo: 
# - Handle if input has [x, -x]. What I did now is to normalize the clause once it get read. However, this will not enable us to 
#   view the initial set provided. Will see only the normalized version. The solution is to write normalize() method in each Clause and Set classes.
#   and in the evaluation loop, we call the method normalize() before to_lo_condition(). However, do we need to normalize each set? or it's just the root set?
#   This needs to be thought of well because we don't want to add extra time in the evaluation loop if we won't need normalization except for the root set.
#   Currently it works fine with the current implementation as it focuses only on root, but we just don't save the unnormalized version for the root set.

# a class to represent the CNF graph
class CnfGraph:

    content = None    

    def __init__(self, content = None):
        self.content = content

    def print_node(self):
        print(self.content)


def Main(args):    
    # determine input type/format
    input_type = None
    input_content = None

    if args.line_input:
        input_type = INPUT_SL
        input_content = args.line_input

    elif args.line_input_file:
        input_type = INPUT_SLF
        input_content = args.line_input_file

    elif args.dimacs:
        input_type = INPUT_DIMACS
        input_content = args.dimacs

    # begin logic
    CnfSet = None
    try:
        input_reader = InputReader(input_type, input_content)
        CnfSet = input_reader.get_cnf_set()

        # start processing the root set
        if len(CnfSet.clauses) > 0 or CnfSet.value != None:
            PAT = PatternSolver(args=args, problem_id=CnfSet.get_hash().hex())
            PAT.solve_set(CnfSet)

    except Exception as e:
        logger.critical("Error - {0}".format(str(e)))
        logger.critical("Error - {0}".format(traceback.format_exc()))
        


if __name__ == "__main__":

    start_time = time.time()
    class Formatter(argparse.RawTextHelpFormatter, argparse.ArgumentDefaultsHelpFormatter): pass
    parser = argparse.ArgumentParser(description="NasserSatSolver [OPTIONS]", formatter_class=argparse.RawTextHelpFormatter)
    group1 = parser.add_mutually_exclusive_group()
    group1.add_argument("-v", "--verbos", help="Verbos", action="store_true")
    group1.add_argument("-vv", "--very-verbos", help="Very verbos", action="store_true")
    group1.add_argument("-q", "--quiet", help="Quiet mode. No stdout output.", action="store_true")
    group2 = parser.add_mutually_exclusive_group(required=True)
    group2.add_argument("-l", "--line-input", type=str, help="Represent the input set in one line. Format: a|b|c&d|e|f ...")
    group2.add_argument("-lf", "--line-input-file", type=argparse.FileType('r'), help="Represent the input set in one line stored in a file. Format: a|b|c&d|e|f ...")
    group2.add_argument("-d", "--dimacs", type=argparse.FileType('r'), help="File name to contain the set in DIMACS format. See http://bit.ly/dimcasf")
    parser.add_argument("-g", "--output-graph-file", type=str, help="Output graph file in Graphviz format")
    parser.add_argument("-ns", "--no-stats", help="Short concise output. No stats about unique numbers and other information. This will disable the global database option.", action="store_true")
    parser.add_argument("-t", "--threads", type=int, help="Number of threads. Value 1 means no multithreading, 0 means max concurrent threads on the machine. This option will implicitly enable the global DB.", default=1)
    parser.add_argument("-e", "--exit-upon-solving", help="Exit whenever a solution is found.", action="store_true")
    parser.add_argument("-rdb", "--use-runtime-db", help="Use database for set lookup in table established only for the current cnf", action="store_true")
    parser.add_argument("-gdb", "--use-global-db", help="Use database for set lookup in global sets table", action="store_true")
    parser.add_argument("-gnm", "--gdb-no-mem", help="Don't load hashes from global DB into memory. Use this only if gdb gets huge and doesn't fit in memory. (slower)", action="store_true")
    parser.add_argument("-m", "--mode", help=textwrap.dedent('''Solution mode. It's either:
    [LO condition is where all variables appear in the ascending order]
    flo: Linearily ordered, where all nodes in the tree will be brought to L.O. condition. (default)
    flop: Linearily ordered, where all nodes in the tree will be brought to L.O. condition, clauses are sorted per size.
    lo: Linearily ordered, where only the root node will be brought to L.O. condition while the rest of the nodes will be brought to L.O.U. condition.
    lou: Linearily ordered universal, where all nodes in the tree will be brought to L.O.U. condition.
    normal: Don't use Nasser's algorithm and use a normal evaluation of the set with no preprocessing steps except for ascending sorting of vars within each clause.
            '''), choices=['flo', 'flop', 'lo', 'lou', 'normal'], default="flo")
    parser.add_argument('--version', action='version', version='%(prog)s ') # can use GitPython to automatically get latest tag here

    # The algorithm
    # --------------
    # START:
    # if FLOP:
    #     place unit clauses first
    # rename vars
    # sort within clauses
    # if FLO or FLOP or (LO root node only):
    #     sort clauses()

    # check if it meets LO condition, if not go to step START


    args = parser.parse_args()

    if args.quiet:
        logger.setLevel(logging.CRITICAL)
    
    # if threads is set, enable gdb
    # if args.threads == 0 or args.threads > 1:
    #     args.use_global_db = True
    if args.threads < 0:
        print("Option -t must be a positive number.")
        parser.print_help()
        sys.exit(3)

    # at least one input must be provided
    if args.line_input == None and args.line_input_file == None and args.dimacs == None:
        print("No input provided. Please provide any of the input arguments.")
        parser.print_help()
        sys.exit(3)

    # only one input must be provided
    if (args.line_input and args.line_input_file) or (args.line_input and args.dimacs) or (args.dimacs and args.line_input_file):
        print("Please provide only one input.")
        parser.print_help()
        sys.exit(3)

    # only use -gnm if -gdb is set
    if args.gdb_no_mem and not args.use_global_db:
        parser.error('-gnm/--gdb-no-mem MUST be used with -gdb/--use-global-db option')


    if args.verbos:
        logger.setLevel(logging.INFO)
    elif args.very_verbos:
        logger.setLevel(logging.DEBUG)
    elif args.quiet:
        logger.setLevel(logging.CRITICAL)

    Main(args)
    
    print('script took %.3f seconds' % (time.time() - start_time))

