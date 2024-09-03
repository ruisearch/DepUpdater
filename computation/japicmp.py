"""use japicmp to check the binary compatibility of one version"""

class Japicmp:
    """japicmp tool class"""
    
    def __init__(self, old_jar:str, new_jar:str):
        """
        Args:
            old_jar (str): the path to the old jar file
            new_jar (str): the path to the new jar file
        """
        self.old_jar = old_jar
        self.new_jar = new_jar
        # the list following are the bin BC records in Japicmp report
        # the content are got from extract_bc_records method
        self.binary_bc_records = []
        # four dict following are bc_api -> bc_record
        # the content are got from extract_bc_api method
        self.binary_bc_method = {}
        self.binary_bc_type = {}
        
    def bc_api(self, groupId: str, artifactId: str, oldVersion: str, newVersion: str):
        """main method of this file, get the bin bc api in the format of dict"""
        # command to check the binary compatibility between two jars
        command = f"japicmp -o {self.old_jar} -n {self.new_jar} -r json"
        # execute the command
        result = os.popen(command).read()
        # parse the result to get the binary compatibility records
        self.binary_bc_records = self.extract_bc_records(result)
        # parse the result to get the binary compatibility api
        self.extract_bc_api(groupId, artifactId, oldVersion, newVersion)