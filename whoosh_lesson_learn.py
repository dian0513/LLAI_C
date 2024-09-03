import os
from whoosh.index import create_in
from whoosh.fields import *
from whoosh.qparser import MultifieldParser, AndGroup
from jieba.analyse import ChineseAnalyzer
from db.db import select_all

# Define the schema, stored=True means the field can be retrieved in search results
schema = Schema(
    ID=ID(stored=True),
    filename=ID(stored=True),
    Development_Dep=ID(stored=True),
    Keywords=TEXT(stored=True, analyzer=ChineseAnalyzer())
)

# Define the table name and retrieve data from the database
table_name = 'LessonLearn_Classification'
LessonLearn_Classification = select_all(table_name)

def clean_content(text):
    return re.sub(r'【[^】]*】', '', text)

LessonLearn_Classification['ID'] = LessonLearn_Classification['ID'].apply(clean_content)
LessonLearn_Classification['filename'] = LessonLearn_Classification['filename'].apply(clean_content)
LessonLearn_Classification['Development_Dep'] = LessonLearn_Classification['Development_Dep'].apply(clean_content)
LessonLearn_Classification['Keyword_EMC'] = LessonLearn_Classification['Keyword_EMC'].apply(clean_content)
LessonLearn_Classification['Keyword_Electric'] = LessonLearn_Classification['Keyword_Electric'].apply(clean_content)
LessonLearn_Classification['Keyword_Component'] = LessonLearn_Classification['Keyword_Component'].apply(clean_content)
LessonLearn_Classification['Keyword_Manufacture'] = LessonLearn_Classification['Keyword_Manufacture'].apply(clean_content)



LessonLearn_Classification_list = LessonLearn_Classification.values.tolist()
# Create the index directory if it doesn't exist
indexdir = 'indexdir/'
if not os.path.exists(indexdir):
    os.mkdir(indexdir)

# Create the index
ix = create_in(indexdir, schema)

# Add documents to the index
writer = ix.writer()
for record in LessonLearn_Classification_list:
    ID, filename, Development_Dep, Keyword_EMC, Keyword_Electric,Keyword_Component,Keyword_Manufacture = record
    writer.add_document(
        ID=str(ID),  # Convert ID to string
        filename=filename,
        Development_Dep=Development_Dep,
        Keywords=Keyword_EMC+' '+Keyword_Electric+' '+Keyword_Component+' '+Keyword_Manufacture
    )
writer.commit()

# Search for the keyword "LED" in the page_text field
def whoosh_query(query):
    searcher = ix.searcher()
    # Split the query by commas to handle multiple terms
    query_terms = query.split(',')

    # Initialize the parser for the "page_text" field
    parser = MultifieldParser(["Keywords"], ix.schema, group=AndGroup)

    # Combine queries using AND operator to ensure all terms must be present
    combined_query = None
    keyword_dict = {}
    for term in query_terms:
        parsed_query = parser.parse(term)
        keyword_list = str(parsed_query).replace('Keywords', '').replace('(', '').replace(')', '').replace(':',
                                                                                                            '').split(
            'AND')
        keyword_dict[term] = keyword_list
        if combined_query is None:
            combined_query = parser.parse(term)
        else:
            combined_query = combined_query & parser.parse(term)

    # Perform the search
    results = searcher.search(combined_query)

    # Extract and print filenames from search results
    results_list = [(result['filename'], result['ID'], result['Development_Dep']) for result in results]

    # Sort the results by descriptions
    sorted_results = sorted(results_list, key=lambda x: x[1])

    # Separate filenames and descriptions after sorting
    filenames = [filename for filename, id,Development_Dep in sorted_results]
    ids = [id for filename, id,Development_Dep  in sorted_results]
    Development_Deps = [Development_Dep for filename, id,Development_Dep  in sorted_results]


    return filenames, ids, Development_Deps


