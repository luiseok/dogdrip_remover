from remover.dogdrip import DogdripRemover

if __name__ == "__main__":
    dogdrip = DogdripRemover()
    if dogdrip.login():
        dogdrip.fetch_comment_list()
        # dogdrip.fetch_document_list()
        dogdrip.collect_comment_details()
        # dogdrip.collect_document_details()
        dogdrip.delete_all_comments_job()
        # dogdrip.delete_all_documents_job()