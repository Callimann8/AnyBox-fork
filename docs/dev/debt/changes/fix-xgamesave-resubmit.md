# xgameruntime

## change [a second write or delete of one blob in an update]

- [XGameSave](../../../core/libs/xdll/xgameruntime/GameSave.cpp) (xgameruntime) - behaviour the documentation does not state: a null pointer argument returns `E_INVALIDARG`, as does an empty blob name or a second write or delete of one blob in an update; a change or a second submit while an asynchronous submit of the same update is pending returns `E_GS_HANDLE_EXPIRED`, and a submit that fails leaves the update open for another submit; deleting a missing blob or container succeeds; `XGameSaveGetContainerInfo` on a missing container returns `S_OK` without calling back; a null display name in `XGameSaveCreateUpdate` keeps the stored one; `XGameSaveReadBlobData` with null `blobNames` and a count of 0 reads every blob; the read buffer holds the `XGameSaveBlob` array followed by each blob's name and data, and a buffer that is too small returns `E_GS_PROVIDED_BUFFER_TOO_SMALL`; the blob name length limit is not enforced; host I/O failures return `E_GS_OUT_OF_LOCAL_STORAGE` for a full disk and the Win32 error otherwise
  Closes when: measured on a console title
